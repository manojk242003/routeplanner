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
    """
    Visualize maritime route with optional canal jumps.
    """

    # ================= LOAD ROUTE =================
    with open(route_json_path, "r") as f:
        data = json.load(f)

    route = data.get("route_smooth") or data.get("route")
    start = data["start"]
    goal = data["goal"]
    canal_jumps = data.get("canal_jumps", [])

    # ================= CREATE MAP =================
    center_lat = (start[0] + goal[0]) / 2
    center_lon = (start[1] + goal[1]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # ================= MAIN ROUTE =================
    folium.PolyLine(
        route,
        color="blue",
        weight=4,
        opacity=0.8,
        tooltip="Maritime Route",
    ).add_to(m)

    # ================= CANAL JUMPS =================
    for jump in canal_jumps:
        p_from = jump["from"]
        p_to = jump["to"]
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
        all_points.append(jump["from"])
        all_points.append(jump["to"])

    m.fit_bounds(all_points)

    # ================= SAVE & OPEN =================
    m.save(output_html)
    print(f"[OK] Map saved to {output_html}")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_html)}")
