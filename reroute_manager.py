import json
import pickle
from grid import snap_to_grid, get_neighbors
from astar import astar
from smoothing import douglas_peucker
from geoutils import haversine
from config import VESSEL_SPEED_KMPH

# ============================================================
# LOAD OCEAN GRID
# ============================================================

with open("valid_nodes.pkl", "rb") as f:
    VALID_NODES_LIST = pickle.load(f)

VALID_NODES = set(VALID_NODES_LIST)
print(f"[REROUTE] Loaded {len(VALID_NODES):,} valid ocean nodes")


# ============================================================
# LOAD WEATHER CACHE
# ============================================================

with open("weather_cache.pkl", "rb") as f:
    WEATHER_CACHE = pickle.load(f)

print(f"[REROUTE] Weather cache loaded: {len(WEATHER_CACHE):,} grid points")


# ============================================================
# HELPERS
# ============================================================

def snap_to_valid_node(point):
    """Snap lat/lon to nearest valid ocean grid node"""
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

    # Fallback brute force
    return min(
        VALID_NODES,
        key=lambda v: (v[0] - lat) ** 2 + (v[1] - lon) ** 2
    )


def make_ocean_neighbors():
    """Neighbor function with ocean validation"""
    def ocean_neighbors(node):
        return [n for n in get_neighbors(node) if n in VALID_NODES]
    return ocean_neighbors


# ============================================================
# STORM CHECKER
# ============================================================

def storm_checker(lat, lon):
    """
    Returns storm risk [0..1] for a given position
    Uses the weather cache
    """
    key = (round(lat, 1), round(lon, 1))
    if key in WEATHER_CACHE:
        return WEATHER_CACHE[key].get("storm_risk", 0.0)
    return 0.0


# ============================================================
# STORM-AWARE COST FUNCTION
# ============================================================

def storm_aware_cost(a, b):
    """
    Travel time cost with storm penalty
    Higher cost in storm zones to make A* avoid them
    """
    dist_km = haversine(a, b)
    base_time = dist_km / VESSEL_SPEED_KMPH
    
    # Check storm risk at destination point
    risk = storm_checker(b[0], b[1])
    
    # Apply penalty (higher risk = higher cost)
    # Penalty multiplier: 1x normal, up to 6x in severe storms
    penalty = 1.0 + (5.0 * risk)
    
    return base_time * penalty


# ============================================================
# REROUTE FUNCTION
# ============================================================

def compute_reroute(current_pos, goal, storm_penalty=5.0, smooth=True):
    """
    Computes a NEW route from current position to goal
    AVOIDING detected storms using A* with storm awareness
    
    Args:
        current_pos: (lat, lon) tuple - current ship position
        goal: (lat, lon) tuple - destination
        storm_penalty: float - how much to penalize storm zones (default 5.0)
        smooth: bool - whether to smooth the path
    
    Returns:
        dict with new route information
    """
    
    print("\n" + "="*60)
    print("🌀 REROUTING IN PROGRESS")
    print("="*60)
    
    # Snap to valid grid nodes
    print(f"[REROUTE] Current position: {current_pos}")
    start = snap_to_valid_node(snap_to_grid(current_pos))
    print(f"[REROUTE] Snapped start: {start}")
    
    print(f"[REROUTE] Goal: {goal}")
    goal_snapped = snap_to_valid_node(snap_to_grid(goal))
    print(f"[REROUTE] Snapped goal: {goal_snapped}")
    
    # Create neighbor function
    neighbor_fn = make_ocean_neighbors()
    
    # Run A* with storm avoidance
    print(f"[REROUTE] Starting A* search with storm avoidance...")
    print(f"[REROUTE] Storm penalty factor: {storm_penalty}x")
    
    try:
        raw_path = astar(
            start=start,
            goal=goal_snapped,
            neighbor_fn=neighbor_fn,
            cost_fn=storm_aware_cost,
            max_speed_kmph=VESSEL_SPEED_KMPH,
            storm_checker=storm_checker,
            storm_penalty=storm_penalty,
        )
        
        print(f"[REROUTE] ✅ New path found! ({len(raw_path)} waypoints)")
        
        # Smooth the path
        if smooth:
            print("[REROUTE] Smoothing new route...")
            route = douglas_peucker(raw_path, epsilon_km=1.0)
            print(f"[REROUTE] Smoothed to {len(route)} waypoints")
        else:
            route = raw_path
        
        # Calculate route statistics
        total_distance = sum(
            haversine(route[i], route[i+1]) 
            for i in range(len(route)-1)
        )
        
        # Count waypoints in storm zones
        storm_waypoints = sum(
            1 for wp in route 
            if storm_checker(wp[0], wp[1]) > 0.3
        )
        
        print("="*60)
        print("✅ REROUTE SUCCESSFUL")
        print(f"   New route distance: {total_distance:.1f} km")
        print(f"   Waypoints: {len(route)}")
        print(f"   Storm waypoints: {storm_waypoints} ({100*storm_waypoints/len(route):.1f}%)")
        print("="*60 + "\n")
        
        return {
            "route_raw": raw_path,
            "route_smooth": route,
            "num_waypoints_raw": len(raw_path),
            "num_waypoints_smooth": len(route),
            "total_distance_km": total_distance,
            "storm_waypoints": storm_waypoints,
            "success": True
        }
        
    except RuntimeError as e:
        print(f"[REROUTE] ❌ FAILED: {e}")
        print("="*60 + "\n")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# SAVE UPDATED ROUTE
# ============================================================

def save_updated_route(new_route, start, goal, filename="route.json"):
    """
    Saves the updated route to route.json
    This allows visualise_route.py to show the new path
    """
    data = {
        "route_smooth": new_route,
        "route_raw": new_route,  # same for now
        "start": start,
        "goal": goal,
        "num_waypoints": len(new_route)
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"[REROUTE] Updated route saved to {filename}")


# ============================================================
# MAIN REROUTE HANDLER (for integration with main.py)
# ============================================================

def handle_reroute(current_pos, goal, save_route=True, storm_penalty=10.0):
    """
    Main function to call when storm is detected
    
    Args:
        current_pos: (lat, lon) - current ship position
        goal: (lat, lon) - final destination
        save_route: bool - whether to save updated route to route.json
        storm_penalty: float - penalty factor for storm zones (higher = more avoidance)
    
    Returns:
        new route (list of waypoints) or None if failed
    """
    result = compute_reroute(current_pos, goal, storm_penalty=storm_penalty)
    
    if result["success"]:
        new_route = result["route_smooth"]
        
        if save_route:
            save_updated_route(new_route, list(current_pos), list(goal))
        
        return new_route
    else:
        print("⚠️ Rerouting failed - ship may need manual intervention")
        return None


# ============================================================
# TEST STANDALONE
# ============================================================

if __name__ == "__main__":
    # Test rerouting from a position where storm was detected
    # Based on your output: storm detected at hour 22, position (11.25, 75.50)
    
    print("🧪 TESTING REROUTE MANAGER\n")
    
    # Load original route to get goal
    with open("route.json", "r") as f:
        route_data = json.load(f)
    
    current_position = (11.25, 75.50)  # Where storm was detected
    goal = tuple(route_data["goal"])
    
    print(f"Test scenario:")
    print(f"  Current position: {current_position}")
    print(f"  Goal: {goal}")
    print(f"  Storm detected ahead - computing alternate route...\n")
    
    new_route = handle_reroute(current_position, goal, save_route=True)
    
    if new_route:
        print(f"\n✅ Test successful - new route has {len(new_route)} waypoints")
        print("You can now run visualise_route.py to see the updated route")
    else:
        print("\n❌ Test failed - could not find alternate route")
