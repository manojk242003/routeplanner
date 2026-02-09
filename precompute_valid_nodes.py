# # precompute_valid_nodes.py

# import pickle
# from landmask import LandMask
# from bathymetry import Bathymetry

# # ================= CONFIG =================
# GRID_RESOLUTION = 0.25       # finer grid → connectivity
# VESSEL_DRAFT = 8.0           # meters

# # Asia bounds
# LAT_MIN, LAT_MAX = -10.0, 80.0
# LON_MIN, LON_MAX = 25.0, 180.0


# # ==========================================

# land_mask = LandMask("data/ne_10m_land/ne_10m_land.shp")
# bathymetry = Bathymetry("data/bathymetry/GEBCO_2024.nc")

# VALID_NODES = set()

# lat = LAT_MIN
# while lat <= LAT_MAX:
#     lon = LON_MIN
#     while lon <= LON_MAX:
#         lat_r = round(lat, 3)
#         lon_r = round(lon, 3)

#         if land_mask.is_ocean(lat_r, lon_r) and bathymetry.is_safe(lat_r, lon_r, VESSEL_DRAFT):
#             VALID_NODES.add((lat_r, lon_r))

#         lon += GRID_RESOLUTION
#     lat += GRID_RESOLUTION

# with open("valid_nodes.pkl", "wb") as f:
#     pickle.dump(VALID_NODES, f)

# print(f"[OK] Precomputed {len(VALID_NODES)} valid nodes")

import pickle
from landmask import LandMask
from bathymetry import Bathymetry
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# ================= CONFIG =================
GRID_RESOLUTION = 0.25
VESSEL_DRAFT = 15

LAT_MIN, LAT_MAX = -80.0, 80.0
LON_MIN, LON_MAX = -180.0, 180.0
# =========================================

land_mask = None
bathymetry = None

def init_worker():
    global land_mask, bathymetry
    land_mask = LandMask("data/ne_10m_land/ne_10m_land.shp")
    bathymetry = Bathymetry("data/bathymetry/GEBCO_2024.nc")

def process_lat(lat):
    nodes = set()
    lon = LON_MIN

    while lon <= LON_MAX:
        lat_r = round(lat, 3)
        lon_r = round(lon, 3)

        if land_mask.is_ocean(lat_r, lon_r) and bathymetry.is_safe(lat_r, lon_r, VESSEL_DRAFT):
            nodes.add((lat_r, lon_r))

        lon += GRID_RESOLUTION

    return nodes

def main():
    VALID_NODES = set()

    latitudes = []
    lat = LAT_MIN
    while lat <= LAT_MAX:
        latitudes.append(lat)
        lat += GRID_RESOLUTION

    print(f"[INFO] Processing {len(latitudes)} latitude slices...")

    try:
        with Pool(cpu_count(), initializer=init_worker) as pool:
            for nodes in tqdm(pool.imap_unordered(process_lat, latitudes),
                              total=len(latitudes)):
                VALID_NODES.update(nodes)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted. Terminating workers...")
        pool.terminate()
        pool.join()
        print("[INFO] Workers terminated.")

    with open("valid_nodes_suez.pkl", "wb") as f:
        pickle.dump(VALID_NODES, f)

    print(f"[OK] Precomputed {len(VALID_NODES)} valid nodes")

if __name__ == "__main__":
    main()


# precompute_valid_nodes.py

# precompute_valid_nodes.py

# import pickle
# import time
# from landmask import LandMask
# from bathymetry import Bathymetry

# # ================= CONFIG =================
# GRID_RESOLUTION = 0.25
# VESSEL_DRAFT = 8.0

# LAT_MIN, LAT_MAX = -56.0, 83.0
# LON_MIN, LON_MAX = -168.0, -34.0
# # ==========================================

# land_mask = LandMask("data/ne_10m_land/ne_10m_land.shp")
# bathymetry = Bathymetry("data/bathymetry/GEBCO_2024.nc")

# is_ocean = land_mask.is_ocean
# is_safe = bathymetry.is_safe

# # Precompute grid
# lat_values = [
#     round(LAT_MIN + i * GRID_RESOLUTION, 3)
#     for i in range(int((LAT_MAX - LAT_MIN) / GRID_RESOLUTION) + 1)
# ]

# lon_values = [
#     round(LON_MIN + i * GRID_RESOLUTION, 3)
#     for i in range(int((LON_MAX - LON_MIN) / GRID_RESOLUTION) + 1)
# ]

# VALID_NODES = set()

# total_lat_steps = len(lat_values)
# start_time = time.time()

# print("started")

# for done, lat in enumerate(lat_values, start=1):
#     for lon in lon_values:
#         # First check land (cheap)
#         if not is_ocean(lat, lon):
#             continue

#         # Only then check bathymetry (expensive)
#         if is_safe(lat, lon, VESSEL_DRAFT):
#             VALID_NODES.add((lat, lon))

#     elapsed = time.time() - start_time
#     progress = (done / total_lat_steps) * 100
#     eta = (elapsed / done) * (total_lat_steps - done)

#     print(
#         f"\rProgress: {progress:6.2f}% "
#         f"| Lat bands: {done}/{total_lat_steps} "
#         f"| ETA: {eta/60:5.1f} min",
#         end="",
#         flush=True,
#     )

# print()  # newline

# with open("valid_nodes.pkl", "wb") as f:
#     pickle.dump(VALID_NODES, f)

# print(f"[OK] Precomputed {len(VALID_NODES)} valid nodes")
