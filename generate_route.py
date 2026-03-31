#!/usr/bin/env python3
"""
Run this BEFORE starting voyage simulation to reset the route
"""
#generate_route.py
import json
from planner import compute_route
from locations import LOCATIONS


Start = LOCATIONS["vizag"]

Goal = LOCATIONS["tokyo"]
print("="*70)
print("GENERATING FRESH ROUTE: Start → goal")
print("="*70)
print(f"Start: Start {Start}")
print(f"Goal:  Goal {Goal}")
print()

# Compute the route
result = compute_route(
    start=Start,
    # goal=SINGAPORE,
    goal = Goal,
    smooth=True
)

# Save to route.json
route_data = {
    "route_smooth": result["route_smooth"],
    "route_raw": result["route_raw"],
    "start": Start,
    "goal": Goal,
    "num_waypoints": result["num_waypoints_smooth"]
}

with open("route.json", "w") as f:
    json.dump(route_data, f, indent=2)

print()
print("="*70)
print("✅ ROUTE GENERATED SUCCESSFULLY")
print("="*70)
print(f"Waypoints: {result['num_waypoints_smooth']}")
print(f"Raw waypoints: {result['num_waypoints_raw']}")
print(f"Saved to: route.json")
print()
print("Now you can run:")
print("  1. python main_v2.py        (to simulate voyage)")
print("  2. python visualise_voyage.py  (to visualize)")
print("="*70)
