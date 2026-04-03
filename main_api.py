import os
import uuid
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File
from planner import compute_route
from visualize_route import visualize_route
from typing import Optional, List
from pydantic import BaseModel
import pandas as pd
import io

app = FastAPI()

from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="maritime_route_app")

def get_coordinates(city_name: str):
    location = geolocator.geocode(city_name)
    if not location:
        raise ValueError(f"City not found: {city_name}")
    return (location.latitude, location.longitude)


# ---------------- CORS ----------------
origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MAPS DIRECTORY ----------------
MAPS_DIR = "maps"
os.makedirs(MAPS_DIR, exist_ok=True)

# Serve static maps
app.mount("/maps", StaticFiles(directory=MAPS_DIR), name="maps")


# ---------------- REQUEST MODEL ----------------
class RouteRequest(BaseModel):
    start: Optional[List[float]] = None
    goal: Optional[List[float]] = None
    startCity: Optional[str] = None
    goalCity: Optional[str] = None
    averageSpeed: int

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):

    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

    results = []

    for index, row in df.iterrows():

        try:
            # ---------------- SPEED ----------------
            vessel_speed_kmph = float(row["averageSpeed"]) * 1.852

            # ---------------- START ----------------
            if not pd.isna(row["startLatitude"]) and not pd.isna(row["startLongitude"]):
                start = (
                    float(row["startLatitude"]),
                    float(row["startLongitude"]),
                )
            elif not pd.isna(row["startPort"]):
                start = get_coordinates(row["startPort"])
            else:
                raise ValueError("Start location missing")

            # ---------------- GOAL ----------------
            if not pd.isna(row["destLatitude"]) and not pd.isna(row["destLongitude"]):
                goal = (
                    float(row["destLatitude"]),
                    float(row["destLongitude"]),
                )
            elif not pd.isna(row["destPort"]):
                goal = get_coordinates(row["destPort"])
            else:
                raise ValueError("Destination location missing")

            # ---------------- COMPUTE ROUTE ----------------
            result = compute_route(start, goal, vessel_speed_kmph, smooth=True)

            # ---------------- UNIQUE MAP ----------------
            map_id = uuid.uuid4().hex
            route_json_path = os.path.join(MAPS_DIR, f"{map_id}.json")
            map_html_path = os.path.join(MAPS_DIR, f"{map_id}.html")

            route_payload = {
                "start": start,
                "goal": goal,
                "route_smooth": result["route_smooth"],
                "canal_jumps": result.get("canal_jumps", []),
                "travel_time_hours": result["travel_time_hours"],
            }

            with open(route_json_path, "w") as f:
                json.dump(route_payload, f, indent=2)

            visualize_route(
                route_json_path=route_json_path,
                output_html=map_html_path,
                open_browser=False,
            )

            results.append({
                "row": index + 1,
                "map_url": f"http://localhost:8000/maps/{map_id}.html",
                "travel_time_hours": result["travel_time_hours"],
            })

        except Exception as e:
            results.append({
                "row": index + 1,
                "error": str(e),
            })

    return {
        "total_rows": len(df),
        "processed": len(results),
        "results": results
    }

# ---------------- API ENDPOINT ----------------
@app.post("/api/route")
def generate_route(request: RouteRequest):

    try:
        print("[INFO] Incoming request:", request)

        # ---------------- Resolve Start ----------------
        if request.startCity:
            print("[INFO] Geocoding start city:", request.startCity)
            start = get_coordinates(request.startCity)
        elif request.start:
            start = tuple(request.start)
        else:
            raise ValueError("Start location missing")

        # ---------------- Resolve Goal ----------------
        if request.goalCity:
            print("[INFO] Geocoding goal city:", request.goalCity)
            goal = get_coordinates(request.goalCity)
        elif request.goal:
            goal = tuple(request.goal)
        else:
            raise ValueError("Goal location missing")

        # ---------------- Speed Conversion ----------------
        # Convert knots → km/h
        vessel_speed_kmph = request.averageSpeed * 1.852

        print(f"[INFO] Start: {start}")
        print(f"[INFO] Goal : {goal}")
        print(f"[INFO] Speed: {vessel_speed_kmph} km/h")

        # ---------------- Compute Route ----------------
        result = compute_route(start, goal, vessel_speed_kmph, smooth=True)

        # ---------------- Generate Unique Map ID ----------------
        map_id = uuid.uuid4().hex

        route_json_path = os.path.join(MAPS_DIR, f"{map_id}.json")
        map_html_path = os.path.join(MAPS_DIR, f"{map_id}.html")

        # ---------------- Save route.json ----------------
        route_payload = {
            "start": start,
            "goal": goal,
            "route_smooth": result["route_smooth"],
            "canal_jumps": result.get("canal_jumps", []),
            "travel_time_hours": result["travel_time_hours"],
            "num_waypoints_raw": result["num_waypoints_raw"],
            "num_waypoints_smooth": result["num_waypoints_smooth"],
            "max_storm_risk": result["max_storm_risk"],
            "avg_storm_risk": result["avg_storm_risk"],
        }

        with open(route_json_path, "w") as f:
            json.dump(route_payload, f, indent=2)

        # ---------------- Generate HTML Map ----------------
        visualize_route(
            route_json_path=route_json_path,
            output_html=map_html_path,
            open_browser=False,
        )

        print(f"[INFO] Map generated → {map_id}.html")

        # ---------------- Return Response ----------------
        return {
            "map_url": f"http://localhost:8000/maps/{map_id}.html",
            "travel_time_hours": result["travel_time_hours"],
            "num_waypoints": result["num_waypoints_smooth"],
            "max_storm_risk": result["max_storm_risk"],
            "avg_storm_risk": result["avg_storm_risk"],
        }

    except Exception as e:
        print("[ERROR]", str(e))
        return {"error": str(e)}
