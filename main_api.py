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
    maxFuel:      float               # km — required, used for efficient route


# ────────────────────────── ROUTES ──────────────────────────────

@app.post("/api/route")
def generate_route(request: RouteRequest):
    try:
        print("[INFO] Incoming request:", request)

        start = resolve_location(request.startCity, request.start, "Start")
        goal  = resolve_location(request.goalCity,  request.goal,  "Goal")

        # Convert knots → km/h  (1 knot = 1.852 km/h)
        vessel_speed_kmph = request.averageSpeed * 1.852

        print(f"[INFO] Start    : {start}")
        print(f"[INFO] Goal     : {goal}")
        print(f"[INFO] Speed    : {vessel_speed_kmph:.1f} km/h")
        print(f"[INFO] Max fuel : {request.maxFuel} km")

        # ----------- COMPUTE BOTH ROUTES (mirrors main.py) -----------
        print("\n[INFO] Computing FASTEST route...")
        res_fastest = compute_route(start, goal, vessel_speed_kmph, smooth=True, mode="fastest")

        print("\n[INFO] Computing EFFICIENT route (with refueling)...")
        res_efficient = compute_route_with_refueling(start, goal, request.maxFuel, vessel_speed_kmph, smooth=True, mode="efficient")

        # ----------- SAVE COMBINED JSON (mirrors main.py) -----------
        map_id = uuid.uuid4().hex
        route_json_path = os.path.join(MAPS_DIR, f"{map_id}.json")
        map_html_path   = os.path.join(MAPS_DIR, f"{map_id}.html")

        output = {
            "start":    list(start),
            "goal":     list(goal),
            "fastest":  res_fastest,
            "efficient": res_efficient,
        }

        with open(route_json_path, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n[OK] route.json written → {map_id}.json")

        # ----------- VISUALIZE -----------
        visualize_route(
            route_json_path=route_json_path,
            output_html=map_html_path,
            open_browser=False,
        )

        print(f"[INFO] Map generated → {map_id}.html")

        return {
            "map_url": f"http://localhost:8000/maps/{map_id}.html",
            "fastest": {
                "travel_time_hours":  res_fastest["travel_time_hours"],
                "num_waypoints":      res_fastest["num_waypoints_smooth"],
                "max_storm_risk":     res_fastest["max_storm_risk"],
                "avg_storm_risk":     res_fastest["avg_storm_risk"],
                "high_risk_waypoints":res_fastest["high_risk_waypoints"],
                "canal_jumps":        res_fastest.get("canal_jumps", []),
            },
            "efficient": {
                "travel_time_hours":  res_efficient["travel_time_hours"],
                "num_waypoints":      res_efficient["num_waypoints_smooth"],
                "max_storm_risk":     res_efficient["max_storm_risk"],
                "avg_storm_risk":     res_efficient["avg_storm_risk"],
                "high_risk_waypoints":res_efficient["high_risk_waypoints"],
                "canal_jumps":        res_efficient.get("canal_jumps", []),
                "port_sequence":      res_efficient.get("port_sequence", []),
            },
        }

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

            max_fuel = float(row.get("maxFuel", 5000))

            # ── compute both routes (mirrors main.py) ──
            print(f"\n[INFO] Row {index + 1}: Computing FASTEST route...")
            res_fastest = compute_route(start, goal, vessel_speed_kmph, smooth=True, mode="fastest")

            print(f"[INFO] Row {index + 1}: Computing EFFICIENT route...")
            res_efficient = compute_route_with_refueling(start, goal, max_fuel, vessel_speed_kmph, smooth=True, mode="efficient")

            # ── save combined JSON ──
            map_id = uuid.uuid4().hex
            route_json_path = os.path.join(MAPS_DIR, f"{map_id}.json")
            map_html_path   = os.path.join(MAPS_DIR, f"{map_id}.html")

            output = {
                "start":     list(start),
                "goal":      list(goal),
                "fastest":   res_fastest,
                "efficient": res_efficient,
            }

            with open(route_json_path, "w") as f:
                json.dump(output, f, indent=2)

            visualize_route(
                route_json_path=route_json_path,
                output_html=map_html_path,
                open_browser=False,
            )

            results.append({
                "row":     index + 1,
                "map_url": f"http://localhost:8000/maps/{map_id}.html",
                "fastest": {
                    "travel_time_hours": res_fastest["travel_time_hours"],
                    "canal_jumps":       res_fastest.get("canal_jumps", []),
                },
                "efficient": {
                    "travel_time_hours": res_efficient["travel_time_hours"],
                    "port_sequence":     res_efficient.get("port_sequence", []),
                    "canal_jumps":       res_efficient.get("canal_jumps", []),
                },
            })

        except Exception as e:
            results.append({"row": index + 1, "error": str(e)})

    return {
        "total_rows": len(df),
        "processed":  len(results),
        "results":    results,
    }