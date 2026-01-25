# main.py

import json
from planner import compute_route
from visualize_route import visualize_route


def read_coord(prompt):
    """
    Reads latitude and longitude from user input.
    Example input: 34.0522 -118.2437
    """
    while True:
        try:
            values = input(prompt).strip().split()
            if len(values) != 2:
                raise ValueError
            lat, lon = map(float, values)
            return (lat, lon)
        except ValueError:
            print("❌ Invalid input. Please enter: <latitude> <longitude>")


if __name__ == "__main__":
    print("=== Maritime Route Planner ===")
    print("Enter coordinates as: latitude longitude\n")

    # ----------- RUNTIME INPUT -----------
    start = read_coord("Enter START  (lat lon): ")
    goal  = read_coord("Enter GOAL   (lat lon): ")

    print("\n[INFO] Start:", start)
    print("[INFO] Goal :", goal)

    # ----------- COMPUTE ROUTE -----------
    result = compute_route(start, goal, smooth=True)

    # ----------- SAVE TO route.json -----------
    output = {
        "start": start,
        "goal": goal,

        # routes
        "route_raw": result["route_raw"],
        "route_smooth": result["route_smooth"],

        # canal info
        "canal_jumps": result.get("canal_jumps", []),

        # stats
        "travel_time_hours": result["travel_time_hours"],
        "num_waypoints_raw": result["num_waypoints_raw"],
        "num_waypoints_smooth": result["num_waypoints_smooth"],
        "max_storm_risk": result["max_storm_risk"],
        "avg_storm_risk": result["avg_storm_risk"],
        "high_risk_waypoints": result["high_risk_waypoints"],
    }

    with open("route.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n[OK] route.json written successfully")

    # ----------- SUMMARY -----------
    print("\n===== ROUTE SUMMARY =====")
    print("Raw waypoints     :", result["num_waypoints_raw"])
    print("Smoothed waypoints:", result["num_waypoints_smooth"])
    print("Travel time (hrs) :", result["travel_time_hours"])
    print("Canal jumps       :", len(result.get("canal_jumps", [])))

    if result.get("canal_jumps"):
        for c in result["canal_jumps"]:
            print(f" - {c['canal'].upper()} canal (+{c['penalty_hours']} hrs)")

    # ----------- VISUALIZE (IMPORTANT FIX) -----------
    print("\n[INFO] Launching route visualization...")
    visualize_route(
        route_json_path="route.json",
        output_html="route_map.html",
        open_browser=True,
    )
