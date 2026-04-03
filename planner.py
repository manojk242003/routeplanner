# planner.py

import pickle
import csv
import heapq
from grid import snap_to_grid, get_neighbors
from astar import astar
from smoothing import douglas_peucker
from geoutils import haversine
from weather import WeatherField, SpeedModel
from config import VESSEL_SPEED_KMPH

# ================= LOAD PRECOMPUTED GRID =================

with open("valid_nodes_world.pkl", "rb") as f:
    VALID_NODES_LIST = pickle.load(f)

VALID_NODES = set(VALID_NODES_LIST)
print(f"[INFO] Loaded {len(VALID_NODES):,} valid nodes")

weather = WeatherField("weather_cache.pkl")
speed_model = SpeedModel()


# ================= LOAD PORTS =================

PORTS = {}
try:
    with open("asia_europe_russia_africa_ports.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = float(row["lat"])
            lon = float(row["lon"])
            # Snap port to a valid ocean node to ensure we can actually route to it
            node = min(
                VALID_NODES,
                key=lambda v: (v[0] - lat) ** 2 + (v[1] - lon) ** 2
            )
            PORTS[row["name"]] = node
    print(f"[INFO] Loaded {len(PORTS)} ports for refueling")
except FileNotFoundError:
    print("[WARN] Port definitions not found. Fuel-constrained routing will not work.")


# ================= CANAL REGISTRY =================

CANALS = {
    "panama": {
        "pacific":  (8.95, -79.55),
        "atlantic": (9.35, -79.90),
        "penalty_hours": 10.0,
    },
    "suez": {
        "south": (29.90, 32.55),   # Red Sea
        "north": (31.25, 32.35),   # Mediterranean
        "penalty_hours": 12.0,
    }
}


# ================= REGION HELPERS =================

def in_americas(coord):
    lat, lon = coord
    return -60.0 <= lat <= 70.0 and -170.0 <= lon <= -30.0

def is_pacific(coord):
    return coord[1] < -100.0

def is_atlantic(coord):
    return coord[1] > -80.0

def in_afro_eurasia(coord):
    lat, lon = coord
    return -40.0 <= lat <= 70.0 and -20.0 <= lon <= 135.0

def is_red_sea(coord):
    return 12.0 <= coord[0] <= 30.0 and 32.0 <= coord[1] <= 44.0

def is_mediterranean(coord):
    return 30.0 <= coord[0] <= 46.0 and -6.0 <= coord[1] <= 36.0


# ======== BASIN HELPERS (ADDED) ========

def is_indian_indopacific(coord):
    lat, lon = coord
    return (
        40.0 <= lon <= 130.0 and
        -40.0 <= lat <= 40
    )

def is_europe_mediterranean(coord):
    lat, lon = coord
    return (
        -10.0 <= lon <= 40.0 and
        30.0 <= lat <= 70.0
    )


# ================= HELPERS =================

# Virtual connections for narrow straits that the grid missed
EXTRA_EDGES = {
    (40.5, 26.5): [(40.5, 27.0)],
    (40.5, 27.0): [(40.5, 26.5)],
}

def snap_to_valid_node(point):
    lat, lon = point
    # Wrap negative longitudes
    lon = lon % 360.0
    return min(
        VALID_NODES,
        key=lambda v: (v[0] - lat) ** 2 + (v[1] - lon) ** 2
    )

def make_ocean_neighbors():
    def ocean_neighbors(node):
        neighbors = [n for n in get_neighbors(node) if n in VALID_NODES]
        if node in EXTRA_EDGES:
            for extra in EXTRA_EDGES[node]:
                if extra in VALID_NODES:
                    neighbors.append(extra)
        return neighbors
    return ocean_neighbors


# ================= COST FUNCTION =================

def time_cost(a, b,VESSEL_SPEED_KMPH, search_mode=True):
    dist = haversine(a, b)

    wave_h = weather.wave_height(*a)
    wave_dir = weather.wave_direction(*a)
    storm = weather.storm_risk(*a)

    speed = speed_model.effective_speed(
        VESSEL_SPEED_KMPH,
        wave_h,
        wave_dir,
        ship_heading=None,
        storm_risk=storm,
    )

    t = dist / speed

    if search_mode:
        if storm > 0.3:
            t *= (1 + storm * 1.5)
    else:
        if storm > 0.3:
            t *= (1 + (storm ** 3) * 100)
        if storm > 0.1:
            t *= (1 + storm * 2)

    return t

def distance_cost(a, b, search_mode=True):
    return haversine(a, b) / VESSEL_SPEED_KMPH


# ================= CANAL HANDLER =================

def route_via_canal(start, goal, canal_name, side_a, side_b,VESSEL_SPEED_KMPH,mode="fastest"):
    canal = CANALS[canal_name]

    a = snap_to_valid_node(snap_to_grid(canal[side_a]))
    b = snap_to_valid_node(snap_to_grid(canal[side_b]))

    print(f"[INFO] Routing via {canal_name.upper()} Canal")

    neighbors = make_ocean_neighbors()
    cost_fn = time_cost

    path1 = astar(
        start, a, neighbors,
        lambda x, y: cost_fn(x, y, True),
        VESSEL_SPEED_KMPH,
    )

    path2 = astar(
        b, goal, neighbors,
        lambda x, y: cost_fn(x, y, True),
        VESSEL_SPEED_KMPH,
    )

    canal_jump = {
        "from": a,
        "to": b,
        "canal": canal_name,
        "penalty_hours": canal["penalty_hours"],
    }

    return path1[:-1], canal_jump, path2[1:]


# ================= MAIN API =================

def compute_route(start, goal, VESSEL_SPEED_KMPH,smooth=True,mode="fastest"):
    start = snap_to_valid_node(snap_to_grid(start))
    goal  = snap_to_valid_node(snap_to_grid(goal))

    print("[INFO] Snapped start:", start)
    print("[INFO] Snapped goal :", goal)

    neighbors = make_ocean_neighbors()
    canal_jumps = []
    raw_path = []

    # ---------- PANAMA ----------
    if (
        in_americas(start) and in_americas(goal) and
        ((is_pacific(start) and is_atlantic(goal)) or
         (is_atlantic(start) and is_pacific(goal)))
    ):
        if is_pacific(start):
            p1, jump, p2 = route_via_canal(start, goal, "panama", "pacific", "atlantic", mode)
        else:
            p1, jump, p2 = route_via_canal(start, goal, "panama", "atlantic", "pacific", mode)

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- SUEZ (FIXED) ----------
    elif (
        # Indo-Pacific (India / China / SE Asia) ↔ Europe
        (is_indian_indopacific(start) and is_europe_mediterranean(goal)) or
        (is_europe_mediterranean(start) and is_indian_indopacific(goal)) or

        # Local Red Sea ↔ Mediterranean
        (
            in_afro_eurasia(start) and in_afro_eurasia(goal) and
            ((is_red_sea(start) and is_mediterranean(goal)) or
             (is_mediterranean(start) and is_red_sea(goal)))
        )
    ):
        if is_indian_indopacific(start) or is_red_sea(start):
            p1, jump, p2 = route_via_canal(start, goal, "suez", "south", "north", mode)
        else:
            p1, jump, p2 = route_via_canal(start, goal, "suez", "north", "south", mode)

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- DIRECT ----------
    else:
        cost_fn = time_cost
        raw_path = astar(
            start, goal, neighbors,
            lambda a, b: cost_fn(a, b, True),
            VESSEL_SPEED_KMPH,
        )

    # ---------- SMOOTHING ----------
    smoothed = douglas_peucker(raw_path, epsilon_km=10.0) if smooth else raw_path

    # ---------- FINAL ETA ----------
    cost_fn = time_cost
    total_time = sum(
        cost_fn(smoothed[i], smoothed[i + 1], False)
        for i in range(len(smoothed) - 1)
    )

    for c in canal_jumps:
        total_time += c["penalty_hours"]

    storms = [weather.storm_risk(*p) for p in smoothed]

    return {
        "route_raw": raw_path,
        "route_smooth": smoothed,
        "canal_jumps": canal_jumps,
        "travel_time_hours": round(total_time, 2),
        "num_waypoints_raw": len(raw_path),
        "num_waypoints_smooth": len(smoothed),
        "max_storm_risk": round(max(storms), 2) if storms else 0.0,
        "avg_storm_risk": round(sum(storms) / len(storms), 2) if storms else 0.0,
        "high_risk_waypoints": sum(1 for s in storms if s > 0.5),
    }

def compute_route_with_refueling(start, goal, max_fuel_range_km, smooth=True, mode="fastest"):
    """
    Computes a route that guarantees no single leg exceeds max_fuel_range_km, 
    by stopping at ports when necessary.
    Uses A* on a virtual graph of ports.
    """
    start_snapped = snap_to_valid_node(snap_to_grid(start))
    goal_snapped  = snap_to_valid_node(snap_to_grid(goal))

    print(f"\n[INFO] Fuel-Constrained Routing (Max {max_fuel_range_km} km)")

    # 1. Build Port Graph + Start/Goal
    nodes = {"START": start_snapped, "GOAL": goal_snapped}
    for name, node in PORTS.items():
        nodes[name] = node

    # 2. Port Graph A* Helper Functions
    def port_neighbors(current_key):
        current_node = nodes[current_key]
        neighbors = []
        for n_key, n_node in nodes.items():
            if n_key == current_key:
                continue
            dist = haversine(current_node, n_node)
            # Use 0.8 as a safety factor since direct hauling might cross land
            if dist <= max_fuel_range_km * 0.8:
                neighbors.append(n_key)
        # Always allow trying goal directly if it's within optimistic range
        if "GOAL" not in neighbors and haversine(current_node, nodes["GOAL"]) <= max_fuel_range_km:
            neighbors.append("GOAL")
        return neighbors

    def port_cost(a_key, b_key):
        return haversine(nodes[a_key], nodes[b_key])

    # 3. A* on Port Graph
    open_heap = [(0.0, "START")]
    came_from = {}
    g_cost = {"START": 0.0}
    closed_set = set()

    found_sequence = None

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current == "GOAL":
            path = [current]
            curr = current
            while curr in came_from:
                curr = came_from[curr]
                path.append(curr)
            found_sequence = path[::-1]
            break

        if current in closed_set:
            continue
        closed_set.add(current)

        for neighbor in port_neighbors(current):
            if neighbor in closed_set:
                continue
            
            tentative_g = g_cost[current] + port_cost(current, neighbor)
            
            if neighbor not in g_cost or tentative_g < g_cost[neighbor]:
                g_cost[neighbor] = tentative_g
                h = haversine(nodes[neighbor], nodes["GOAL"])
                f = tentative_g + h
                heapq.heappush(open_heap, (f, neighbor))
                came_from[neighbor] = current

    if not found_sequence:
        print("[WARN] No valid refueling sequence found. Proceeding with direct route.")
        return compute_route(start, goal, smooth, mode)

    print(f"[INFO] Optimal port sequence: {' -> '.join(found_sequence)}")

    # 4. Stitch actual ocean routes between the sequence
    full_route_raw = []
    full_route_smooth = []
    full_canal_jumps = []
    total_time = 0.0
    all_storms = []

    for i in range(len(found_sequence) - 1):
        seg_start = nodes[found_sequence[i]]
        seg_goal = nodes[found_sequence[i+1]]
        
        print(f"       Computing leg: {found_sequence[i]} -> {found_sequence[i+1]}")
        seg_result = compute_route(seg_start, seg_goal, smooth, mode)
        
        # Avoid duplicating the overlapping waypoints
        if i > 0 and len(seg_result["route_raw"]) > 0:
            full_route_raw.extend(seg_result["route_raw"][1:])
        else:
            full_route_raw.extend(seg_result["route_raw"])
            
        if i > 0 and len(seg_result["route_smooth"]) > 0:
            full_route_smooth.extend(seg_result["route_smooth"][1:])
        else:
            full_route_smooth.extend(seg_result["route_smooth"])
            
        full_canal_jumps.extend(seg_result.get("canal_jumps", []))
        total_time += seg_result["travel_time_hours"]
        
        # Recalculate combined storm risk
        all_storms.extend([weather.storm_risk(*p) for p in seg_result["route_smooth"]])

    return {
        "route_raw": full_route_raw,
        "route_smooth": full_route_smooth,
        "canal_jumps": full_canal_jumps,
        "travel_time_hours": round(total_time, 2),
        "num_waypoints_raw": len(full_route_raw),
        "num_waypoints_smooth": len(full_route_smooth),
        "max_storm_risk": round(max(all_storms), 2) if all_storms else 0.0,
        "avg_storm_risk": round(sum(all_storms) / len(all_storms), 2) if all_storms else 0.0,
        "high_risk_waypoints": sum(1 for s in all_storms if s > 0.5),
        "port_sequence": found_sequence,
    }
