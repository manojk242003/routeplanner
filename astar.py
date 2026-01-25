# astar.py

import heapq
from tqdm import tqdm
from geoutils import haversine
from config import GOAL_THRESHOLD_KM, MAX_EXPANSIONS


# ================= HEURISTIC =================

def heuristic(a, b, max_speed_kmph):
    # optimistic (admissible) time estimate
    return haversine(a, b) / max_speed_kmph


# ================= PATH RECONSTRUCTION =================

def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]


# ================= A* SEARCH =================

def astar(start, goal, neighbor_fn, cost_fn, max_speed_kmph):
    open_heap = [(0.0, start)]
    came_from = {}
    g_cost = {start: 0.0}
    
    # OPTIMIZATION: Track closed set to avoid re-expanding nodes
    closed_set = set()

    expansions = 0

    pbar = tqdm(
        total=MAX_EXPANSIONS,
        desc="A* Search",
        unit="nodes",
        dynamic_ncols=True,
    )

    while open_heap:
        _, current = heapq.heappop(open_heap)
        
        # Skip if already expanded
        if current in closed_set:
            continue
        
        closed_set.add(current)
        expansions += 1
        pbar.update(1)

        if expansions >= MAX_EXPANSIONS:
            pbar.close()
            raise RuntimeError(f"A* expansion limit exceeded ({MAX_EXPANSIONS:,} nodes)")

        # Goal check
        if haversine(current, goal) <= GOAL_THRESHOLD_KM:
            pbar.close()
            print(f"[A*] Goal reached after {expansions:,} expansions")
            return reconstruct_path(came_from, current)

        for neighbor in neighbor_fn(current):
            if neighbor in closed_set:
                continue
                
            tentative_g = g_cost[current] + cost_fn(current, neighbor)

            if neighbor not in g_cost or tentative_g < g_cost[neighbor]:
                g_cost[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal, max_speed_kmph)
                heapq.heappush(open_heap, (f, neighbor))
                came_from[neighbor] = current

    pbar.close()
    raise RuntimeError("No route found - search space exhausted")