"""
Maritime Voyage Simulation with Real-Time Weather (FINAL FIXED)

✔ Fetches real weather every 5 hours
✔ Proper realtime updates
✔ Rerouting works
✔ Visualization compatible
✔ No KeyErrors
"""

import json
import pickle
import time
import math
from datetime import datetime

from realtime_weather_fetcher import build_realtime_cache
from realtime_weather import RealtimeWeatherField
from reroute_manager import handle_reroute


# ============================================================
# CONFIG
# ============================================================

WEATHER_UPDATE_INTERVAL_HOURS = 5
LOOKAHEAD_WAYPOINTS = 10

STORM_THRESHOLD_REROUTE = 0.7
MIN_WAYPOINTS_BEFORE_REROUTE = 3
MAX_REROUTES = 10

SHIP_SPEED = 35


# ============================================================
# HELPERS
# ============================================================

def haversine(a, b):
    R = 6371
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))


def format_time(hours):
    d = int(hours // 24)
    h = int(hours % 24)
    m = int((hours - int(hours)) * 60)
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


# ============================================================
# MAIN
# ============================================================

def run_voyage():

    print("\n" + "="*60)
    print("🚢 VOYAGE STARTED")
    print("="*60)

    # ---------- LOAD ROUTE ----------
    with open("route.json") as f:
        route_data = json.load(f)

    ORIGINAL_ROUTE = route_data["route_smooth"].copy()
    ORIGINAL_START = route_data["start"]
    ORIGINAL_GOAL = route_data["goal"]

    route = route_data["route_smooth"]
    FINAL_GOAL = tuple(ORIGINAL_GOAL)

    print(f"Start: {ORIGINAL_START}")
    print(f"Goal : {ORIGINAL_GOAL}")
    print(f"Waypoints: {len(route)}\n")

    # ---------- STATIC CACHE ----------
    with open("weather_cache.pkl", "rb") as f:
        static_cache = pickle.load(f)

    print("🌦️ Static weather loaded")

    # ---------- REALTIME ----------
    rt_weather = RealtimeWeatherField()

    # ---------- SHIP ----------
    ship = {
        "current_index": 0,
        "time": 0,
        "reroutes": 0,
        "last_reroute_pos": None,
        "waypoints_since_reroute": 0,
        "last_weather_update": -999,
        "positions": []
    }

    # ============================================================
    # LOOP
    # ============================================================

    while ship["current_index"] < len(route) - 1:

        lat, lon = route[ship["current_index"]]

        # STORE POSITION (IMPORTANT FOR VISUALIZATION)
        ship["positions"].append((lat, lon))

        ship["time"] += 1

        print(f"\n⏱️ Hour {ship['time']}")
        print(f"📍 Position: ({lat:.2f}, {lon:.2f})")

        # ================= WEATHER UPDATE =================
        if ship["time"] - ship["last_weather_update"] >= WEATHER_UPDATE_INTERVAL_HOURS:

            print("\n🌊 FETCHING REAL-TIME WEATHER DATA\n")

            end_idx = min(ship["current_index"] + LOOKAHEAD_WAYPOINTS, len(route))
            lookahead = route[ship["current_index"]:end_idx]

            build_realtime_cache(lookahead)

            rt_weather = RealtimeWeatherField()  # reload

            ship["last_weather_update"] = ship["time"]

            print("✅ Weather updated\n")

        # ================= CURRENT WEATHER =================
        data = rt_weather.get_full_data(lat, lon)

        risk = data.get("storm_risk", 0) if data else 0

        print(f"🌩️ Current Storm Risk: {risk:.2f}")

        # ================= LOOKAHEAD =================
        storm_detected = False
        storm_location = None
        max_risk = 0

        for i in range(1, LOOKAHEAD_WAYPOINTS):

            idx = ship["current_index"] + i
            if idx >= len(route):
                break

            la, lo = route[idx]
            d = rt_weather.get_full_data(la, lo)

            if d:
                r = d.get("storm_risk", 0)

                if r > max_risk:
                    max_risk = r
                    storm_location = (la, lo)

                if r > STORM_THRESHOLD_REROUTE:
                    storm_detected = True
                    break

        # ================= REROUTE =================
        if storm_detected:

            print(f"⚠️ Storm ahead at {storm_location} Risk={max_risk:.2f}")

            current_pos = (lat, lon)

            if ship["last_reroute_pos"] == current_pos:
                print("⚠️ Already rerouted here")
            elif ship["waypoints_since_reroute"] < MIN_WAYPOINTS_BEFORE_REROUTE:
                print("⚠️ Too soon to reroute")
            elif ship["reroutes"] >= MAX_REROUTES:
                print("⚠️ Max reroutes reached")
            else:
                print("🌀 REROUTING...\n")

                new_route = handle_reroute(
                    current_pos,
                    FINAL_GOAL,
                    save_route=False,
                    storm_penalty=10 + ship["reroutes"] * 2
                )

                if new_route:
                    route = new_route
                    ship["current_index"] = 0
                    ship["reroutes"] += 1
                    ship["last_reroute_pos"] = current_pos
                    ship["waypoints_since_reroute"] = 0

                    print("✅ Reroute successful\n")
                    continue
                else:
                    print("❌ Reroute failed")

        # ================= MOVE =================
        ship["current_index"] += 1
        ship["waypoints_since_reroute"] += 1

        print("➡️ Moving forward...")

        time.sleep(0.2)

    # ============================================================
    # COMPLETE
    # ============================================================

    print("\n" + "="*60)
    print("🏁 VOYAGE COMPLETED")
    print("="*60)

    print(f"Time: {ship['time']} hours")
    print(f"Reroutes: {ship['reroutes']}")

    # ✅ FIXED OUTPUT (THIS WAS YOUR MAIN ISSUE)
    voyage_data = {
        "original_start": ORIGINAL_START,
        "original_goal": ORIGINAL_GOAL,
        "original_route": ORIGINAL_ROUTE,
        "ship_path": ship["positions"],
        "final_route": route,
        "total_hours": ship["time"],
        "reroutes": ship["reroutes"],
        "completed": True
    }

    with open("voyage_data.json", "w") as f:
        json.dump(voyage_data, f, indent=2)

    print("📁 Saved: voyage_data.json")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    run_voyage()
