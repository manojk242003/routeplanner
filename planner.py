# planner.py

import pickle
from grid import snap_to_grid, get_neighbors
from astar import astar
from smoothing import douglas_peucker
from geoutils import haversine
from config import VESSEL_SPEED_KMPH


# ============================================================
# LOAD PRECOMPUTED OCEAN GRID
# ============================================================

with open("valid_nodes.pkl", "rb") as f:
    VALID_NODES_LIST = pickle.load(f)

VALID_NODES = set(VALID_NODES_LIST)
print(f"[INFO] Loaded {len(VALID_NODES):,} valid ocean nodes")


# ============================================================
# HELPERS
# ============================================================

def snap_to_valid_node(point):
    """
    Snap lat/lon to nearest valid ocean grid node
    Optimized radius-based search
    """
    lat, lon = point
    search_radius = 0.1
    max_radius = 2.0

    while search_radius <= max_radius:
        best = None
        best_dist = float("inf")

        for v in VALID_NODES:
            if abs(v[0] - lat) > search_radius or abs(v[1] - lon) > search_radius:
                continue

            d = (v[0] - lat) ** 2 + (v[1] - lon) ** 2
            if d < best_dist:
                best_dist = d
                best = v

        if best is not None:
            return best

        search_radius *= 2

    # Fallback brute force (should almost never happen)
    return min(
        VALID_NODES,
        key=lambda v: (v[0] - lat) ** 2 + (v[1] - lon) ** 2
    )


def make_ocean_neighbors():
    """
    Neighbor function with O(1) ocean lookup
    """
    def ocean_neighbors(node):
        return [n for n in get_neighbors(node) if n in VALID_NODES]
    return ocean_neighbors


# ============================================================
# FAST COST FUNCTION (NO WEATHER, NO TIME)
# ============================================================

def base_time_cost(a, b):
    """
    Simple distance-based travel time
    Used ONLY for route planning
    """
    dist_km = haversine(a, b)
    return dist_km / VESSEL_SPEED_KMPH


# ============================================================
# MAIN ROUTE PLANNER (WEATHER-AGNOSTIC)
# ============================================================

def compute_route(start, goal, smooth=True):
    """
    Computes a BASELINE ocean route.
    Weather, time, storms are handled later during voyage simulation.
    """

    print("[INFO] Snapping start point...")
    start = snap_to_valid_node(snap_to_grid(start))

    print("[INFO] Snapping goal point...")
    goal = snap_to_valid_node(snap_to_grid(goal))

    print("[INFO] Snapped start:", start)
    print("[INFO] Snapped goal :", goal)

    neighbor_fn = make_ocean_neighbors()

    print("[INFO] Starting FAST A* search (no weather)...")
    raw_path = astar(
        start=start,
        goal=goal,
        neighbor_fn=neighbor_fn,
        cost_fn=base_time_cost,
        max_speed_kmph=VESSEL_SPEED_KMPH,
    )

    if smooth:
        print("[INFO] Smoothing route...")
        route = douglas_peucker(raw_path, epsilon_km=1.0)
    else:
        route = raw_path

    print("[INFO] Base route planning completed")

    return {
        "route_raw": raw_path,
        "route_smooth": route,
        "num_waypoints_raw": len(raw_path),
        "num_waypoints_smooth": len(route),
    }
