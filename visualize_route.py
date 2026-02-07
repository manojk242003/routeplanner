# visualize_route.py

import json
import folium
import webbrowser
import os


def visualize_route(
    route_json_path="route.json",
    output_html="route_map.html",
    open_browser=True,
):
    # ================= LOAD DATA =================
    with open(route_json_path, "r") as f:
        data = json.load(f)

    # FORCE full route usage (NO fallback)
    route = data["route_smooth"]
    route = [(float(lat), float(lon)) for lat, lon in route]

    start = tuple(data["start"])
    goal = tuple(data["goal"])
    canal_jumps = data.get("canal_jumps", [])

    # ================= MAP INIT =================
    m = folium.Map(
        location=route[0],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # ================= MAIN ROUTE =================
    folium.PolyLine(
        route,
        color="blue",
        weight=4,
        opacity=0.85,
        tooltip="Maritime Route",
    ).add_to(m)

    # ================= CANAL JUMPS =================
    for jump in canal_jumps:
        p_from = tuple(jump["from"])
        p_to = tuple(jump["to"])
        canal = jump["canal"].upper()
        penalty = jump["penalty_hours"]

        folium.PolyLine(
            [p_from, p_to],
            color="red",
            weight=4,
            opacity=0.9,
            dash_array="6,6",
            tooltip=f"{canal} Canal (+{penalty} hrs)",
        ).add_to(m)

        folium.CircleMarker(
            p_from,
            radius=6,
            color="red",
            fill=True,
            popup=f"{canal} Canal Entry",
        ).add_to(m)

        folium.CircleMarker(
            p_to,
            radius=6,
            color="red",
            fill=True,
            popup=f"{canal} Canal Exit",
        ).add_to(m)

    # ================= START / GOAL =================
    folium.Marker(
        start,
        popup="Start",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    folium.Marker(
        goal,
        popup="Goal",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    # ================= FIT BOUNDS =================
    all_points = route[:]
    for jump in canal_jumps:
        all_points.append(tuple(jump["from"]))
        all_points.append(tuple(jump["to"]))

    m.fit_bounds(all_points)

    # ================= SAVE & OPEN =================
    m.save(output_html)
    print(f"[OK] Map saved to {output_html}")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_html)}")
