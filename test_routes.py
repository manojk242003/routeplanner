# test_routes.py

import json
from planner import compute_route
from visualize_route import visualize_route


# ================= TEST CASES =================
# Covers:
# - Americas (Panama)
# - India ↔ Europe (Suez)
# - Asia ↔ Europe (Suez)
# - Short sanity Suez routes
# - Long-haul stress tests

TEST_CASES = [

    # -------- AMERICAS (PANAMA VALIDATION) --------
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
        "name": "San Francisco → Rio de Janeiro",
        "start": (37.7749, -122.4194),
        "goal": (-22.9068, -43.1729),
    },

    # -------- SOUTH AMERICA COASTAL --------
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

    # # -------- INDIA ↔ EUROPE (SUEZ CORE) --------
    # {
    #     "name": "Mumbai → Rotterdam (Suez)",
    #     "start": (19.0760, 72.8777),
    #     "goal": (51.9244, 4.4777),
    # },
    # {
    #     "name": "Chennai → Marseille (Suez)",
    #     "start": (13.0827, 80.2707),
    #     "goal": (43.2965, 5.3698),
    # },
    # {
    #     "name": "Kochi → Piraeus (Suez)",
    #     "start": (9.9312, 76.2673),
    #     "goal": (37.9420, 23.6469),
    # },

    # # -------- ASIA ↔ EUROPE (SUEZ HEAVY LOAD) --------
    # {
    #     "name": "Singapore → Hamburg (Suez)",
    #     "start": (1.3521, 103.8198),
    #     "goal": (53.5511, 9.9937),
    # },
    # {
    #     "name": "Shanghai → Genoa (Suez)",
    #     "start": (31.2304, 121.4737),
    #     "goal": (44.4056, 8.9463),
    # },

    # # -------- SHORT SUEZ SANITY CHECKS --------
    # {
    #     "name": "Jeddah → Istanbul (Suez)",
    #     "start": (21.4858, 39.1925),
    #     "goal": (41.0082, 28.9784),
    # },
    # {
    #     "name": "Dubai → Athens (Suez)",
    #     "start": (25.2048, 55.2708),
    #     "goal": (37.9838, 23.7275),
    # },

    # # -------- LONG HAUL STRESS TEST --------
    # {
    #     "name": "London → Yokohama (Suez)",
    #     "start": (51.5074, -0.1278),
    #     "goal": (35.4437, 139.6380),
    # },

    # # -------- FAILURE / COMPARISON DEMO --------
    # {
    #     "name": "Singapore → Rotterdam (Suez vs Cape of Good Hope)",
    #     "start": (1.3521, 103.8198),
    #     "goal": (51.9244, 4.4777),
    # },
]


# ================= RUNNER =================

def run_test(test):
    print("\n==============================")
    print(f"Running: {test['name']}")
    print("==============================")

    result = compute_route(
        test["start"],
        test["goal"],
        smooth=True
    )

    output = {
        "name": test["name"],
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
    print(f"Travel time (hrs): {result['travel_time_hours']:.2f}")

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
