#visualise_route.py
import json
import folium
import webbrowser
import os
import pickle

# ================= USER CONTROL =================
hour = 80  # 🔥 CHANGE THIS TO MOVE SHIP
# ===============================================

# ================= LOAD VOYAGE DATA =================
with open("voyage_data.json", "r") as f:
    voyage_data = json.load(f)

original_route = voyage_data["original_route"]
original_start = voyage_data["original_start"]
original_goal = voyage_data["original_goal"]

full_ship_path = voyage_data["ship_path"]      # FULL journey
rerouted_path = voyage_data.get("rerouted_path", [])
reroute_paths = voyage_data.get("reroute_paths", [])

# ================= SLICE BY TIME =================
ship_path = full_ship_path[:min(hour, len(full_ship_path))]
current_pos = ship_path[-1] if ship_path else original_start

# print(f"[INFO] Hour = {hour}")
print(f"[INFO] Ship covered points = {len(ship_path)}")
print(f"[INFO] Total points = {len(full_ship_path)}")

# ================= LOAD WEATHER CACHE =================
with open("weather_cache.pkl", "rb") as f:
    weather_cache = pickle.load(f)

# ================= CREATE MAP =================
center_lat = (original_start[0] + original_goal[0]) / 2
center_lon = (original_start[1] + original_goal[1]) / 2

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=5,
    tiles="OpenStreetMap",
    control_scale=True
)

# ================= ORIGINAL ROUTE (BLUE DASHED) =================
folium.PolyLine(
    original_route,
    color="#4da6ff",
    weight=2,
    opacity=0.4,
    dash_array="6,6",
    tooltip="Original Planned Route"
).add_to(m)

# ================= COVERED PATH (GREEN) =================
if len(ship_path) > 1:
    folium.PolyLine(
        ship_path,
        color="#1f7a1f",
        weight=4,
        tooltip="Ship's Path"
    ).add_to(m)

# ================= REROUTED PATH (ORANGE) =================
if len(rerouted_path) > 1:
    folium.PolyLine(
        rerouted_path,
        color="#ff9800",
        weight=5,
        tooltip="Rerouted Path"
    ).add_to(m)

for idx, rpath in enumerate(reroute_paths):
    if len(rpath) > 1:
        folium.PolyLine(
            rpath,
            color="#ff9800",
            weight=5,
            tooltip=f"Reroute Segment {idx+1}"
        ).add_to(m)

# ================= STORMS =================
# ================= STORMS (PROFESSIONAL HEATMAP STYLE) =================
from folium.plugins import HeatMap

storm_points = []
all_positions = original_route + ship_path

for (lat, lon), info in weather_cache.items():
    risk = info["storm_risk"]

    if risk > 0.5 and any(abs(lat-p[0]) + abs(lon-p[1]) < 3 for p in all_positions):
        # Heatmap expects [lat, lon, intensity]
        storm_points.append([lat, lon, risk])

storm_count = len(storm_points)

if storm_points:
    HeatMap(
        storm_points,
        min_opacity=0.3,
        max_zoom=7,
        radius=35,
        blur=45,
        gradient={
            0.5: '#ffcc80',   # light orange
            0.7: '#ff9800',   # orange
            0.85: '#ff5722',  # deep orange-red
            1.0: '#b71c1c'    # deep red
        }
    ).add_to(m)


# ================= CURRENT SHIP POSITION =================
folium.Marker(
    current_pos,
    popup=f"🚢 Ship Position<br>Hour {hour}",
    icon=folium.Icon(color="green", icon="ship", prefix="fa"),
).add_to(m)

# ================= START & GOAL =================
folium.Marker(
    original_start,
    icon=folium.Icon(color="green", icon="play", prefix="fa"),
    tooltip="Start"
).add_to(m)

folium.Marker(
    original_goal,
    icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
    tooltip="Destination"
).add_to(m)

# ================= VOYAGE STATS BOX =================
stats_html = f"""
<div style="
    position: fixed;
    top: 20px;
    right: 20px;
    width: 260px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
    z-index: 9999;
    font-family: Arial;
    padding: 14px;
">
<h4 style="margin:0 0 10px;">📊 Voyage Statistics</h4>
<hr style="margin:6px 0;">
<p>⏱️ <b>Time:</b> {hour} hours</p>
<p>🔁 <b>Reroutes:</b> {voyage_data.get("reroutes", len(reroute_paths))}</p>
<p>📍 <b>Positions:</b> {len(ship_path)}</p>
<p>✅ <b>Status:</b> {"Completed" if hour >= len(full_ship_path) else "In Progress"}</p>
</div>
"""
m.get_root().html.add_child(folium.Element(stats_html))

# ================= LEGEND BOX =================
legend_html = """
<div style="
    position: fixed;
    bottom: 30px;
    right: 20px;
    width: 260px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3);
    z-index: 9999;
    font-family: Arial;
    padding: 14px;
">
<h4 style="margin:0 0 10px;">🧭 Route Legend</h4>
<hr style="margin:6px 0;">
<p><span style="color:#1f7a1f;">━━━</span> Ship's Path</p>
<p><span style="color:#4da6ff;">┈┈┈</span> Original Route</p>

<hr style="margin:6px 0;">
<p><span style="color:#ff5722;">●</span> Severe Storm (&gt;0.9)</p>
<p><span style="color:#ffc107;">●</span> High Risk (&gt;0.7)</p>
<p><span style="color:#d4b483;">●</span> Moderate (&gt;0.5)</p>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ================= FIT MAP =================
m.fit_bounds(original_route)

# ================= SAVE =================
OUTPUT_HTML = "voyage_map.html"
m.save(OUTPUT_HTML)

print(f"[✓] Map saved → {OUTPUT_HTML}")
print(f"[✓] Storms shown → {storm_count}")

webbrowser.open(f"file://{os.path.abspath(OUTPUT_HTML)}")
#--------------------------------------------------------------------------------------------
