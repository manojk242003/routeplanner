# planner.py

import pickle
import csv
import heapq
from grid import snap_to_grid, get_neighbors
from astar import astar
from smoothing import douglas_peucker
from geoutils import haversine
from config import VESSEL_SPEED_KMPH as DEFAULT_VESSEL_SPEED_KMPH
from weather import WeatherField, SpeedModel


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
    return -40.0 <= lat <= 70.0 and -20.0 <= lon <= 120.0

def is_red_sea(coord):
    return 12.0 <= coord[0] <= 30.0 and 32.0 <= coord[1] <= 44.0

def is_mediterranean(coord):
    return 30.0 <= coord[0] <= 46.0 and -6.0 <= coord[1] <= 36.0


# ======== BASIN HELPERS ========

def is_indian_indopacific(coord):
    lat, lon = coord
    return (
        40.0 <= lon <= 130.0 and
        -40.0 <= lat <= 35.0
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


# ================= COST FUNCTIONS =================

def time_cost(a, b, vessel_speed_kmph, search_mode=True):
    dist = haversine(a, b)

    wave_h   = weather.wave_height(*a)
    wave_dir = weather.wave_direction(*a)
    storm    = weather.storm_risk(*a)

    speed = speed_model.effective_speed(
        vessel_speed_kmph,
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

def distance_cost(a, b, vessel_speed_kmph, search_mode=True):
    return haversine(a, b) / vessel_speed_kmph


# ================= CANAL HANDLER =================

def route_via_canal(start, goal, canal_name, side_a, side_b, vessel_speed_kmph, mode="fastest"):
    canal = CANALS[canal_name]

    a = snap_to_valid_node(snap_to_grid(canal[side_a]))
    b = snap_to_valid_node(snap_to_grid(canal[side_b]))

    print(f"[INFO] Routing via {canal_name.upper()} Canal")

    neighbors = make_ocean_neighbors()

    path1 = astar(
        start, a, neighbors,
        lambda x, y: time_cost(x, y, vessel_speed_kmph, True),
        vessel_speed_kmph,
    )

    path2 = astar(
        b, goal, neighbors,
        lambda x, y: time_cost(x, y, vessel_speed_kmph, True),
        vessel_speed_kmph,
    )

    canal_jump = {
        "from":          a,
        "to":            b,
        "canal":         canal_name,
        "penalty_hours": canal["penalty_hours"],
    }

    return path1[:-1], canal_jump, path2[1:]


# ================= MAIN API =================

def compute_route(start, goal, vessel_speed_kmph=None, smooth=True, mode="fastest"):
    """
    Compute the optimal ocean route between two coordinates.

    Args:
        start               : (lat, lon) tuple
        goal                : (lat, lon) tuple
        vessel_speed_kmph   : cruising speed in km/h; falls back to config default if None
        smooth              : apply Douglas-Peucker smoothing to the path
        mode                : "fastest" (time-optimised) — reserved for future cost variants

    Returns a dict with route_raw, route_smooth, canal_jumps, travel metrics, and storm stats.
    """
    if vessel_speed_kmph is None:
        vessel_speed_kmph = DEFAULT_VESSEL_SPEED_KMPH

    start = snap_to_valid_node(snap_to_grid(start))
    goal  = snap_to_valid_node(snap_to_grid(goal))

    print("[INFO] Snapped start:", start)
    print("[INFO] Snapped goal :", goal)
    print(f"[INFO] Vessel speed : {vessel_speed_kmph:.1f} km/h")

    neighbors  = make_ocean_neighbors()
    canal_jumps = []
    raw_path    = []

    # ---------- PANAMA ----------
    if (
        in_americas(start) and in_americas(goal) and
        ((is_pacific(start) and is_atlantic(goal)) or
         (is_atlantic(start) and is_pacific(goal)))
    ):
        if is_pacific(start):
            p1, jump, p2 = route_via_canal(start, goal, "panama", "pacific", "atlantic", vessel_speed_kmph, mode)
        else:
            p1, jump, p2 = route_via_canal(start, goal, "panama", "atlantic", "pacific", vessel_speed_kmph, mode)

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- SUEZ ----------
    elif (
        (is_indian_indopacific(start) and is_europe_mediterranean(goal)) or
        (is_europe_mediterranean(start) and is_indian_indopacific(goal)) or
        (
            in_afro_eurasia(start) and in_afro_eurasia(goal) and
            ((is_red_sea(start) and is_mediterranean(goal)) or
             (is_mediterranean(start) and is_red_sea(goal)))
        )
    ):
        if is_indian_indopacific(start) or is_red_sea(start):
            p1, jump, p2 = route_via_canal(start, goal, "suez", "south", "north", vessel_speed_kmph, mode)
        else:
            p1, jump, p2 = route_via_canal(start, goal, "suez", "north", "south", vessel_speed_kmph, mode)

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- DIRECT ----------
    else:
        raw_path = astar(
            start, goal, neighbors,
            lambda a, b: time_cost(a, b, vessel_speed_kmph, True),
            vessel_speed_kmph,
        )

    # ---------- SMOOTHING ----------
    smoothed = douglas_peucker(raw_path, epsilon_km=10.0) if smooth else raw_path

    # ---------- FINAL ETA ----------
    total_time = sum(
        time_cost(smoothed[i], smoothed[i + 1], vessel_speed_kmph, False)
        for i in range(len(smoothed) - 1)
    )

    for c in canal_jumps:
        total_time += c["penalty_hours"]

    storms = [weather.storm_risk(*p) for p in smoothed]

    return {
        "route_raw":             raw_path,
        "route_smooth":          smoothed,
        "canal_jumps":           canal_jumps,
        "travel_time_hours":     round(total_time, 2),
        "num_waypoints_raw":     len(raw_path),
        "num_waypoints_smooth":  len(smoothed),
        "max_storm_risk":        round(max(storms), 2)             if storms else 0.0,
        "avg_storm_risk":        round(sum(storms) / len(storms), 2) if storms else 0.0,
        "high_risk_waypoints":   sum(1 for s in storms if s > 0.5),
    }


def compute_route_with_refueling(start, goal, max_fuel_range_km, vessel_speed_kmph=None, smooth=True, mode="fastest"):
    """
    Compute a route that guarantees no single leg exceeds max_fuel_range_km by
    stopping at intermediate ports when necessary.  Uses A* on a virtual port graph,
    then stitches real ocean legs between each consecutive port pair.

    Args:
        start               : (lat, lon) tuple
        goal                : (lat, lon) tuple
        max_fuel_range_km   : maximum range before refueling is required
        vessel_speed_kmph   : cruising speed in km/h; falls back to config default if None
        smooth              : apply Douglas-Peucker smoothing to each leg
        mode                : routing mode passed through to compute_route

    Returns the same dict shape as compute_route, extended with a "port_sequence" key.
    """
    if vessel_speed_kmph is None:
        vessel_speed_kmph = DEFAULT_VESSEL_SPEED_KMPH

    start_snapped = snap_to_valid_node(snap_to_grid(start))
    goal_snapped  = snap_to_valid_node(snap_to_grid(goal))

    print(f"\n[INFO] Fuel-Constrained Routing (Max {max_fuel_range_km} km, {vessel_speed_kmph:.1f} km/h)")

    # 1. Build virtual node graph: START + all ports + GOAL
    nodes = {"START": start_snapped, "GOAL": goal_snapped}
    for name, node in PORTS.items():
        nodes[name] = node

    # 2. Port-graph helpers
    def port_neighbors(current_key):
        current_node = nodes[current_key]
        neighbors = []
        for n_key, n_node in nodes.items():
            if n_key == current_key:
                continue
            dist = haversine(current_node, n_node)
            # 0.8 safety factor — straight-line may cross land
            if dist <= max_fuel_range_km * 0.8:
                neighbors.append(n_key)
        # Always allow a direct attempt to GOAL if within range
        if "GOAL" not in neighbors and haversine(current_node, nodes["GOAL"]) <= max_fuel_range_km:
            neighbors.append("GOAL")
        return neighbors

    def port_cost(a_key, b_key):
        return haversine(nodes[a_key], nodes[b_key])

    # 3. A* on port graph
    open_heap    = [(0.0, "START")]
    came_from    = {}
    g_cost       = {"START": 0.0}
    closed_set   = set()
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
                heapq.heappush(open_heap, (tentative_g + h, neighbor))
                came_from[neighbor] = current

    if not found_sequence:
        print("[WARN] No valid refueling sequence found. Falling back to direct route.")
        return compute_route(start, goal, vessel_speed_kmph, smooth, mode)

    print(f"[INFO] Optimal port sequence: {' -> '.join(found_sequence)}")

    # 4. Stitch real ocean legs between consecutive ports
    full_route_raw    = []
    full_route_smooth = []
    full_canal_jumps  = []
    total_time        = 0.0
    all_storms        = []

    for i in range(len(found_sequence) - 1):
        seg_start = nodes[found_sequence[i]]
        seg_goal  = nodes[found_sequence[i + 1]]

        print(f"       Leg {i + 1}: {found_sequence[i]} → {found_sequence[i + 1]}")
        seg = compute_route(seg_start, seg_goal, vessel_speed_kmph, smooth, mode)

        # Avoid duplicating the shared waypoint between consecutive legs
        if i > 0:
            full_route_raw.extend(seg["route_raw"][1:])
            full_route_smooth.extend(seg["route_smooth"][1:])
        else:
            full_route_raw.extend(seg["route_raw"])
            full_route_smooth.extend(seg["route_smooth"])

        full_canal_jumps.extend(seg.get("canal_jumps", []))
        total_time += seg["travel_time_hours"]
        all_storms.extend(weather.storm_risk(*p) for p in seg["route_smooth"])

    return {
        "route_raw":             full_route_raw,
        "route_smooth":          full_route_smooth,
        "canal_jumps":           full_canal_jumps,
        "travel_time_hours":     round(total_time, 2),
        "num_waypoints_raw":     len(full_route_raw),
        "num_waypoints_smooth":  len(full_route_smooth),
        "max_storm_risk":        round(max(all_storms), 2)               if all_storms else 0.0,
        "avg_storm_risk":        round(sum(all_storms) / len(all_storms), 2) if all_storms else 0.0,
        "high_risk_waypoints":   sum(1 for s in all_storms if s > 0.5),
        "port_sequence":         found_sequence,
    }