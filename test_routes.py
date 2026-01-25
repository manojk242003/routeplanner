# test_routes.py

import json
from planner import compute_route
from visualize_route import visualize_route


# ================= TEST CASES (ONLY AMERICAS) =================

TEST_CASES = [
    # -------- NORTH AMERICA --------
    {
        "name": "Los Angeles → New York (Panama)",
        "start": (34.0522, -118.2437),
        "goal": (40.7128, -74.0060),
    },
    {
        "name": "New York → Los Angeles (Panama reverse)",
        "start": (40.7128, -74.0060),
        "goal": (34.0522, -118.2437),
    },
    {
        "name": "Vancouver → Miami (Panama)", #flag
        "start": (49.2827, -123.1207),
        "goal": (25.7617, -80.1918),
    },
    {
        "name": "Seattle → Houston (Panama)", #flag
        "start": (47.6062, -122.3321),
        "goal": (29.7604, -95.3698),
    },

    # -------- SOUTH AMERICA --------
    {
        "name": "Callao (Peru) → Santos (Brazil)",
        "start": (-12.0464, -77.0428),
        "goal": (-23.9608, -46.3336),
    },
    {
        "name": "Buenos Aires → Valparaíso",
        "start": (-34.6037, -58.3816),
        "goal": (-33.0472, -71.6127),
    },

    # -------- NORTH ↔ SOUTH AMERICA --------
    {
        "name": "San Francisco → Rio de Janeiro",
        "start": (37.7749, -122.4194),
        "goal": (-22.9068, -43.1729),
    },
    {
        "name": "Seattle → Buenos Aires", #flag
        "start": (47.6062, -122.3321),
        "goal": (-34.6037, -58.3816),
    },
]


# ================= RUNNER =================

def run_test(test):
    print("\n==============================")
    print(f"Running: {test['name']}")
    print("==============================")

    result = compute_route(test["start"], test["goal"], smooth=True)

    output = {
        "start": test["start"],
        "goal": test["goal"],
        "route_raw": result["route_raw"],
        "route_smooth": result["route_smooth"],
        "canal_jumps": result.get("canal_jumps", []),
        "travel_time_hours": result["travel_time_hours"],
        "num_waypoints_raw": result["num_waypoints_raw"],
        "num_waypoints_smooth": result["num_waypoints_smooth"],
    }

    with open("route.json", "w") as f:
        json.dump(output, f, indent=2)

    # -------- PRINT SUMMARY --------
    print(f"Waypoints (raw): {result['num_waypoints_raw']}")
    print(f"Waypoints (smooth): {result['num_waypoints_smooth']}")
    print(f"Travel time (hrs): {result['travel_time_hours']}")

    if result.get("canal_jumps"):
        for c in result["canal_jumps"]:
            print(f"Used {c['canal'].upper()} canal (+{c['penalty_hours']} hrs)")
    else:
        print("No canal used")

    # -------- VISUALIZE --------
    print("Opening map...")
    visualize_route(
        route_json_path="route.json",
        output_html="route_map.html",
        open_browser=True,
    )


# ================= MAIN =================

if __name__ == "__main__":
    for test in TEST_CASES:
        run_test(test)
        input("\nPress ENTER for next test...")
