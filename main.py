# main.py

import json
from planner import compute_route, compute_route_with_refueling
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

def read_float(prompt, default=None):
    """Reads a float from user input."""
    while True:
        try:
            val = input(prompt).strip()
            if not val and default is not None:
                return default
            return float(val)
        except ValueError:
            print("❌ Invalid input. Please enter a number.")


if __name__ == "__main__":
    print("=== Maritime Route Planner ===")
    print("Enter coordinates as: latitude longitude\n")

    # ----------- RUNTIME INPUT -----------
    start = read_coord("Enter START  (lat lon): ")
    goal  = read_coord("Enter GOAL   (lat lon): ")
    max_fuel = read_float("Enter max fuel range in km [default 5000]: ", default=5000.0)

    print("\n[INFO] Start:", start)
    print("[INFO] Goal :", goal)
    print(f"[INFO] Max Fuel Range: {max_fuel} km")

    # ----------- COMPUTE ROUTE -----------
    print("\n[INFO] Computing FASTEST route...")
    res_fastest = compute_route(start, goal, smooth=True, mode="fastest")
    
    print("\n[INFO] Computing EFFICIENT route (with refueling)...")
    res_efficient = compute_route_with_refueling(start, goal, max_fuel, smooth=True, mode="efficient")


    # ----------- SAVE TO route.json -----------
    output = {
        "start": start,
        "goal": goal,
        "fastest": res_fastest,
        "efficient": res_efficient,
    }

    with open("route.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n[OK] route.json written successfully")

    # ----------- SUMMARY -----------
    print("\n===== ROUTE SUMMARY =====")
    for mode, res in [("FASTEST", res_fastest), ("EFFICIENT", res_efficient)]:
        print(f"\n--- {mode} ---")
        print(f"Travel time (hrs) : {res['travel_time_hours']}")
        print(f"Waypoints (smooth): {res['num_waypoints_smooth']}")
        
        if "port_sequence" in res and res["port_sequence"]:
            ports_str = " -> ".join(res["port_sequence"])
            print(f"Refueling stops   : {ports_str}")
            
        print(f"Canal jumps       : {len(res.get('canal_jumps', []))}")
        if res.get("canal_jumps"):
            for c in res["canal_jumps"]:
                print(f"  - {c['canal'].upper()} canal (+{c['penalty_hours']} hrs)")

    # ----------- VISUALIZE (IMPORTANT FIX) -----------
    print("\n[INFO] Launching route visualization...")
    visualize_route(
        route_json_path="route.json",
        output_html="route_map.html",
        open_browser=True,
    )
