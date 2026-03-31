#astar.py
import heapq
from geoutils import haversine
from config import GOAL_THRESHOLD_KM, MAX_EXPANSIONS


# ================= HEURISTIC =================

def heuristic(a, b, max_speed_kmph):
    return haversine(a, b) / max_speed_kmph


# ================= PATH RECONSTRUCTION =================

def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]


# ================= A* SEARCH (STORM-AWARE) =================

def astar(
    start,
    goal,
    neighbor_fn,
    cost_fn,
    max_speed_kmph,
    storm_checker=None,
    storm_penalty=5.0,
    early_exit_km=GOAL_THRESHOLD_KM
):
    """
    storm_checker(lat, lon) -> risk [0..1]
    """

    open_heap = [(0.0, start)]
    came_from = {}
    g_cost = {start: 0.0}
    closed_set = set()

    expansions = 0

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue
        closed_set.add(current)

        expansions += 1
        if expansions >= MAX_EXPANSIONS:
            raise RuntimeError("A* expansion limit exceeded")

        # 🎯 Goal reached
        if haversine(current, goal) <= early_exit_km:
            print(f"[A*] Goal reached ({expansions} expansions)")
            return reconstruct_path(came_from, current)

        for neighbor in neighbor_fn(current):
            if neighbor in closed_set:
                continue

            # Base movement cost
            step_cost = cost_fn(current, neighbor)

            # 🌦️ Storm penalty (soft constraint)
            if storm_checker:
                risk = storm_checker(neighbor[0], neighbor[1])
                step_cost *= (1.0 + storm_penalty * risk)

            tentative_g = g_cost[current] + step_cost

            if neighbor not in g_cost or tentative_g < g_cost[neighbor]:
                g_cost[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal, max_speed_kmph)
                heapq.heappush(open_heap, (f, neighbor))
                came_from[neighbor] = current

    raise RuntimeError("No route found")
