# planner.py

import pickle
from grid import snap_to_grid, get_neighbors
from astar import astar
from smoothing import douglas_peucker
from geoutils import haversine
from config import VESSEL_SPEED_KMPH
from weather import WeatherField, SpeedModel


# ================= LOAD PRECOMPUTED GRID =================

with open("valid_nodes.pkl", "rb") as f:
    VALID_NODES_LIST = pickle.load(f)

VALID_NODES = set(VALID_NODES_LIST)
print(f"[INFO] Loaded {len(VALID_NODES):,} valid nodes")

weather = WeatherField("weather_cache.pkl")
speed_model = SpeedModel()


# ================= CANAL REGISTRY =================
# Each canal is a bidirectional graph bridge

CANALS = {
    "panama": {
        "pacific":  (8.95, -79.55),
        "atlantic": (9.35, -79.90),
        "penalty_hours": 10.0,   # average Panama transit
    },
    "suez": {
        "south": (29.90, 32.55),   # Red Sea
        "north": (31.25, 32.35),   # Mediterranean
        "penalty_hours": 12.0,     # average Suez transit
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


# ================= HELPERS =================

def snap_to_valid_node(point):
    lat, lon = point
    return min(
        VALID_NODES,
        key=lambda v: (v[0] - lat) ** 2 + (v[1] - lon) ** 2
    )


def make_ocean_neighbors():
    def ocean_neighbors(node):
        return [n for n in get_neighbors(node) if n in VALID_NODES]
    return ocean_neighbors


# ================= COST FUNCTION =================

def time_cost(a, b, search_mode=True):
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


# ================= CANAL HANDLER =================

def route_via_canal(start, goal, canal_name, side_a, side_b):
    canal = CANALS[canal_name]

    a = snap_to_valid_node(snap_to_grid(canal[side_a]))
    b = snap_to_valid_node(snap_to_grid(canal[side_b]))

    print(f"[INFO] Routing via {canal_name.upper()} Canal")

    neighbors = make_ocean_neighbors()

    path1 = astar(
        start, a, neighbors,
        lambda x, y: time_cost(x, y, True),
        VESSEL_SPEED_KMPH,
    )

    path2 = astar(
        b, goal, neighbors,
        lambda x, y: time_cost(x, y, True),
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

def compute_route(start, goal, smooth=True):
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
            p1, jump, p2 = route_via_canal(start, goal, "panama", "pacific", "atlantic")
        else:
            p1, jump, p2 = route_via_canal(start, goal, "panama", "atlantic", "pacific")

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- SUEZ ----------
    elif (
        in_afro_eurasia(start) and in_afro_eurasia(goal) and
        ((is_red_sea(start) and is_mediterranean(goal)) or
         (is_mediterranean(start) and is_red_sea(goal)))
    ):
        if is_red_sea(start):
            p1, jump, p2 = route_via_canal(start, goal, "suez", "south", "north")
        else:
            p1, jump, p2 = route_via_canal(start, goal, "suez", "north", "south")

        raw_path = p1 + [jump["from"], jump["to"]] + p2
        canal_jumps.append(jump)

    # ---------- DIRECT ----------
    else:
        raw_path = astar(
            start, goal, neighbors,
            lambda a, b: time_cost(a, b, True),
            VESSEL_SPEED_KMPH,
        )

    # ---------- SMOOTHING ----------
    if smooth:
        smoothed = douglas_peucker(raw_path, epsilon_km=10.0)
    else:
        smoothed = raw_path

    # ---------- FINAL ETA ----------
    total_time = sum(
        time_cost(smoothed[i], smoothed[i + 1], False)
        for i in range(len(smoothed) - 1)
    )

    # add canal penalties
    for c in canal_jumps:
        total_time += c["penalty_hours"]

    storms = [weather.storm_risk(*p) for p in smoothed]

    return {
        "route_raw": raw_path,
        "route_smooth": smoothed,
        "canal_jumps": canal_jumps,  # <-- FOR WEB VISUALIZATION
        "travel_time_hours": round(total_time, 2),
        "num_waypoints_raw": len(raw_path),
        "num_waypoints_smooth": len(smoothed),
        "max_storm_risk": round(max(storms), 2),
        "avg_storm_risk": round(sum(storms) / len(storms), 2),
        "high_risk_waypoints": sum(1 for s in storms if s > 0.5),
    }
