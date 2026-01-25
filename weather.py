import pickle
import math

# ======================================================
# SPEED MODEL
# ======================================================

class SpeedModel:
    def effective_speed(
        self,
        base_speed_kmph,
        wave_height,
        wave_dir=None,
        ship_heading=None,
        storm_risk=0.0,
    ):
        speed = base_speed_kmph

        # ---------------- Wave height penalty ----------------
        if wave_height < 1.0:
            pass
        elif wave_height < 2.5:
            speed *= 0.9
        elif wave_height < 4.0:
            speed *= 0.75
        else:
            speed *= 0.6

        # ---------------- Directional penalty ----------------
        if wave_dir is not None and ship_heading is not None:
            rel = abs(wave_dir - ship_heading) % 360
            rel = min(rel, 360 - rel)
            if rel < 45:
                speed *= 0.85
            elif rel < 90:
                speed *= 0.93

        # ---------------- Storm risk penalty ----------------
        if storm_risk > 0.9:
            speed *= 0.1  # extreme storm
        elif storm_risk > 0.5:
            speed *= 0.4  # severe
        elif storm_risk > 0.2:
            speed *= 0.7  # moderate

        # general reduction factor
        speed *= max(1.0 - 0.4 * storm_risk, 0.1)

        return max(speed, 1.0)


# ======================================================
# WEATHER FIELD (CACHED LOOKUP) - OPTIMIZED
# ======================================================

class WeatherField:
    def __init__(self, cache_file):
        print(f"[INFO] Loading weather cache from {cache_file}...")
        with open(cache_file, "rb") as f:
            self.data = pickle.load(f)
        print(f"[INFO] Weather cache loaded: {len(self.data):,} grid points")

    def _key(self, lat, lon):
        # Round to match cache resolution (1 decimal = 0.1 degree)
        return (round(lat, 1), round(lon, 1))

    def wave_height(self, lat, lon):
        return self.data.get(self._key(lat, lon), {}).get("wave_height", 2.0)

    def wave_direction(self, lat, lon):
        return self.data.get(self._key(lat, lon), {}).get("wave_dir")

    def storm_risk(self, lat, lon):
        # Direct lookup - no iteration needed!
        key = self._key(lat, lon)
        return self.data.get(key, {}).get("storm_risk", 0.0)


# ======================================================
# ONE-TIME CACHE BUILDER - OPTIMIZED FOR SPARSE DATA
# ======================================================

def build_dummy_weather_cache(
    lat_min, lat_max, lon_min, lon_max,
    storm_center=(10.0, 85.0),
    storm_radius_km=600,
    output="weather_cache.pkl",
    resolution=1.0,
    storm_intensity_multiplier=1.0  # NEW: Control storm strength
):
    
    data = {}

    def haversine(a, b):
        R = 6371
        lat1, lon1 = map(math.radians, a)
        lat2, lon2 = map(math.radians, b)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return 2 * R * math.asin(math.sqrt(h))

    step = int(1.0 / resolution)
    total_points = 0
    storm_points = 0
    
    print(f"[INFO] Generating weather data with {resolution}° resolution...")
    print(f"[INFO] Coverage: lat {lat_min}° to {lat_max}°, lon {lon_min}° to {lon_max}°")
    print(f"[INFO] STORM CENTER: {storm_center}")
    print(f"[INFO] STORM RADIUS: {storm_radius_km} km")
    print(f"[INFO] STORM INTENSITY: {storm_intensity_multiplier}x")
    
    for lat in range(int(lat_min), int(lat_max), step):
        for lon in range(int(lon_min), int(lon_max), step):
            lat_f = float(lat)
            lon_f = float(lon)

            # wave height: simple sinusoidal
            wave_h = 1.5 + 1.2 * abs(math.sin(math.radians(lat_f)))
            wave_dir = (lon_f * 2) % 360

            # storm intensity based on distance from storm center
            d = haversine((lat_f, lon_f), storm_center)
            if d < storm_radius_km:
                # More intense near center, multiplier allows extreme storms
                storm_risk = max(0.0, min(1.0, (1.0 - d / storm_radius_km) * storm_intensity_multiplier))
                storm_points += 1
                
                # Increase wave height in storm area
                wave_h += 3.0 * storm_risk  # Add up to 3m waves in storm
            else:
                storm_risk = 0.0

            data[(round(lat_f, 1), round(lon_f, 1))] = {
                "wave_height": wave_h,
                "wave_dir": wave_dir,
                "storm_risk": storm_risk,
            }
            total_points += 1

    with open(output, "wb") as f:
        pickle.dump(data, f)

    print(f"[OK] Weather cache written → {output}")
    print(f"[OK] Total grid points: {total_points:,}")
    print(f"[OK] Storm-affected points: {storm_points:,}")
    import os
    file_size_kb = os.path.getsize(output) / 1024
    print(f"[OK] Cache size: {file_size_kb:.1f} KB")