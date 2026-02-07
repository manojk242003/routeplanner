# precompute_valid_nodes_suez.py

import pickle
from grid import snap_to_grid
from config import GRID_RESOLUTION
from landmask import LandMask
from bathymetry import Bathymetry

# ================= SUEZ REGION BOUNDS =================
# Covers India–Europe corridor around Suez

LAT_MIN, LAT_MAX = 10.0, 50.0
LON_MIN, LON_MAX = 20.0, 60.0

OUTPUT_FILE = "valid_nodes_suez.pkl"

print("[INFO] Precomputing SUEZ region valid nodes")

# ================= LOAD DATA =================

land = LandMask("data/ne_10m_land/ne_10m_land.shp")
bathy = Bathymetry("data/bathymetry/GEBCO_2024_TID.nc")

valid_nodes = set()

lat = LAT_MIN
while lat <= LAT_MAX:
    lon = LON_MIN
    while lon <= LON_MAX:
        p = snap_to_grid((lat, lon))

        # 1️⃣ Must be ocean
        if land.is_land(*p):
            lon += GRID_RESOLUTION
            continue

        # 2️⃣ Must be navigable depth
        # Negative = ocean, shallow cutoff at -10m
        if bathy.depth_at(*p) >= -10:
            lon += GRID_RESOLUTION
            continue

        valid_nodes.add(p)
        lon += GRID_RESOLUTION

    lat += GRID_RESOLUTION

# ================= SAVE =================

with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(list(valid_nodes), f)

print(f"[OK] SUEZ valid nodes written → {OUTPUT_FILE}")
print(f"[OK] Total nodes: {len(valid_nodes):,}")
