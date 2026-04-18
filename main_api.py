import os
import uuid
import json

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

import pandas as pd
import io

from geopy.geocoders import Nominatim
from planner import compute_route, compute_route_with_refueling
from visualize_route import visualize_route

app = FastAPI()

geolocator = Nominatim(user_agent="maritime_route_app")


# ─────────────────────────── HELPERS ────────────────────────────

def get_coordinates(city_name: str) -> tuple:
    """Geocode a city name to (lat, lon)."""
    location = geolocator.geocode(city_name)
    if not location:
        raise ValueError(f"City not found: {city_name}")
    return (location.latitude, location.longitude)


def resolve_location(
    city: Optional[str],
    coords: Optional[List[float]],
    label: str,
) -> tuple:
    """Return (lat, lon) from either a city name or explicit coordinates."""
    if city:
        print(f"[INFO] Geocoding {label}: {city}")
        return get_coordinates(city)
    if coords:
        return tuple(coords)
    raise ValueError(f"{label} location missing")


def save_and_visualize(result: dict, start: tuple, goal: tuple) -> str:
    """
    Persist route JSON + HTML map, return the public HTML URL.
    """
    map_id = uuid.uuid4().hex
    route_json_path = os.path.join(MAPS_DIR, f"{map_id}.json")
    map_html_path   = os.path.join(MAPS_DIR, f"{map_id}.html")

    route_payload = {
        "start":  list(start),
        "goal":   list(goal),
        "route_smooth":        result["route_smooth"],
        "canal_jumps":         result.get("canal_jumps", []),
        "travel_time_hours":   result["travel_time_hours"],
        "num_waypoints_raw":   result.get("num_waypoints_raw"),
        "num_waypoints_smooth":result.get("num_waypoints_smooth"),
        "max_storm_risk":      result.get("max_storm_risk"),
        "avg_storm_risk":      result.get("avg_storm_risk"),
        # included when a refueling route was computed
        "port_sequence":       result.get("port_sequence"),
    }

    with open(route_json_path, "w") as f:
        json.dump(route_payload, f, indent=2)

    visualize_route(
        route_json_path=route_json_path,
        output_html=map_html_path,
        open_browser=False,
    )

    print(f"[INFO] Map generated → {map_id}.html")
    return f"http://localhost:8000/maps/{map_id}.html"


# ─────────────────────────── APP SETUP ──────────────────────────

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAPS_DIR = "maps"
os.makedirs(MAPS_DIR, exist_ok=True)
app.mount("/maps", StaticFiles(directory=MAPS_DIR), name="maps")


# ─────────────────────────── MODELS ─────────────────────────────

class RouteRequest(BaseModel):
    # Location – accept either city name OR explicit coordinates
    startCity:  Optional[str]        = None
    start:      Optional[List[float]] = None
    goalCity:   Optional[str]        = None
    goal:       Optional[List[float]] = None

    # Routing parameters
    averageSpeed: float               # knots
    mode:         str  = "fastest"   # "fastest" | "efficient"
    maxFuel:      Optional[float] = None  # km; required for "efficient" mode


# ────────────────────────── ROUTES ──────────────────────────────

@app.post("/api/route")
def generate_route(request: RouteRequest):
    try:
        print("[INFO] Incoming request:", request)

        start = resolve_location(request.startCity, request.start, "Start")
        goal  = resolve_location(request.goalCity,  request.goal,  "Goal")

        # Convert knots → km/h  (1 knot = 1.852 km/h)
        vessel_speed_kmph = request.averageSpeed * 1.852

        print(f"[INFO] Start : {start}")
        print(f"[INFO] Goal  : {goal}")
        print(f"[INFO] Speed : {vessel_speed_kmph:.1f} km/h")
        print(f"[INFO] Mode  : {request.mode}")

        if request.mode == "efficient":
            if request.maxFuel is None:
                raise ValueError("maxFuel is required for 'efficient' mode")
            print(f"[INFO] Max fuel range: {request.maxFuel} km")
            result = compute_route_with_refueling(
                start, goal,
                request.maxFuel,
                smooth=True,
                mode="efficient",
            )
        else:
            result = compute_route(
                start, goal,
                smooth=True,
                mode="fastest",
            )

        map_url = save_and_visualize(result, start, goal)

        response = {
            "map_url":            map_url,
            "travel_time_hours":  result["travel_time_hours"],
            "num_waypoints":      result.get("num_waypoints_smooth"),
            "max_storm_risk":     result.get("max_storm_risk"),
            "avg_storm_risk":     result.get("avg_storm_risk"),
            "high_risk_waypoints":result.get("high_risk_waypoints"),
            "canal_jumps":        result.get("canal_jumps", []),
        }

        if "port_sequence" in result:
            response["port_sequence"] = result["port_sequence"]

        return response

    except Exception as e:
        print("[ERROR]", str(e))
        return {"error": str(e)}


# ─────────────────────── CSV BATCH UPLOAD ───────────────────────

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """
    Process a CSV with columns:
        averageSpeed, mode, maxFuel (optional),
        startLatitude / startLongitude  OR  startPort,
        destLatitude  / destLongitude   OR  destPort
    """
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

    results = []

    for index, row in df.iterrows():
        try:
            vessel_speed_kmph = float(row["averageSpeed"]) * 1.852
            mode = str(row.get("mode", "fastest")).strip().lower()

            # ── resolve start ──
            if not pd.isna(row.get("startLatitude")) and not pd.isna(row.get("startLongitude")):
                start = (float(row["startLatitude"]), float(row["startLongitude"]))
            elif not pd.isna(row.get("startPort", float("nan"))):
                start = get_coordinates(str(row["startPort"]))
            else:
                raise ValueError("Start location missing")

            # ── resolve goal ──
            if not pd.isna(row.get("destLatitude")) and not pd.isna(row.get("destLongitude")):
                goal = (float(row["destLatitude"]), float(row["destLongitude"]))
            elif not pd.isna(row.get("destPort", float("nan"))):
                goal = get_coordinates(str(row["destPort"]))
            else:
                raise ValueError("Destination location missing")

            # ── compute ──
            if mode == "efficient":
                max_fuel = float(row.get("maxFuel", 5000))
                result = compute_route_with_refueling(
                    start, goal,
                    max_fuel,
                    smooth=True,
                    mode="efficient",
                )
            else:
                result = compute_route(
                    start, goal,
                    smooth=True,
                    mode="fastest",
                )

            map_url = save_and_visualize(result, start, goal)

            entry = {
                "row":               index + 1,
                "map_url":           map_url,
                "travel_time_hours": result["travel_time_hours"],
            }
            if "port_sequence" in result:
                entry["port_sequence"] = result["port_sequence"]

            results.append(entry)

        except Exception as e:
            results.append({"row": index + 1, "error": str(e)})

    return {
        "total_rows": len(df),
        "processed":  len(results),
        "results":    results,
    }