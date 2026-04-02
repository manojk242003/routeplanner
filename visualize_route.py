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

    start = tuple(data["start"])
    goal = tuple(data["goal"])

    # ================= MAP INIT =================
    m = folium.Map(
        location=start,
        zoom_start=4,
        tiles="OpenStreetMap", 
        control_scale=True,
    )

    all_points = [start, goal]

    # ================= ROUTES =================
    routes_config = [
        ("fastest", data.get("fastest"), "blue", 4, 0.85, "Fastest Route"),
        ("efficient", data.get("efficient"), "orange", 4, 1.0, "Efficient Route"), # Changed to solid line, Using orange as pure yellow is hard to see on light map, but matching the request intention of visible solid
    ]

    for key, route_data, color, weight, opacity, tooltip_text in routes_config:
        if not route_data:
            continue

        route_smooth = route_data.get("route_smooth", [])
        if not route_smooth:
            continue

        route_coords = [(float(lat), float(lon)) for lat, lon in route_smooth]
        all_points.extend(route_coords)

        folium.PolyLine(
            route_coords,
            color=color,
            weight=weight,
            opacity=opacity,
            tooltip=tooltip_text,
            # removed dash array to ensure solid yellow/orange
        ).add_to(m)

        # Port stops for this route
        if "port_sequence" in route_data and route_data["port_sequence"]:
            # Load ports to get coordinates
            import csv
            ports_coords = {}
            try:
                with open("asia_europe_russia_africa_ports.csv", "r", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        ports_coords[row["name"]] = (float(row["lat"]), float(row["lon"]))
            except FileNotFoundError:
                pass

            for port_name in route_data["port_sequence"]:
                if port_name in ["START", "GOAL"]:
                    continue
                if port_name in ports_coords:
                    p_coord = ports_coords[port_name]
                    all_points.append(p_coord)
                    folium.Marker(
                        p_coord,
                        popup=f"Refueling Stop: {port_name}",
                        icon=folium.Icon(color="orange", icon="info-sign"),
                    ).add_to(m)

        # Canal jumps for this route
        for jump in route_data.get("canal_jumps", []):
            p_from = tuple(jump["from"])
            p_to = tuple(jump["to"])
            canal = jump["canal"].upper()
            penalty = jump["penalty_hours"]

            all_points.extend([p_from, p_to])

            folium.PolyLine(
                [p_from, p_to],
                color="red",
                weight=4,
                opacity=0.9,
                dash_array="6, 6",
                tooltip=f"{canal} Canal (+{penalty} hrs) [{tooltip_text}]",
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
    m.fit_bounds(all_points)

    # ================= SAVE & OPEN =================
    m.save(output_html)
    print(f"[OK] Map saved to {output_html}")

    if open_browser:
        webbrowser.open(f"file://{os.path.abspath(output_html)}")
