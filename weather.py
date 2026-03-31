#weather.py
import pickle
import math

# ======================================================
# SPEED MODEL (SIMPLIFIED + FAST)
# ======================================================

class SpeedModel:
    def effective_speed(
        self,
        base_speed_kmph,
        wave_height,
        storm_risk=0.0,
    ):
        """
        FAST speed model:
        - minimal branching
        - no angles
        - safe lower bounds
        """

        speed = base_speed_kmph

        # -------- Wave penalty --------
        if wave_height >= 4.0:
            speed *= 0.6
        elif wave_height >= 2.5:
            speed *= 0.75
        elif wave_height >= 1.5:
            speed *= 0.9

        # -------- Storm penalty --------
        if storm_risk > 0.8:
            speed *= 0.2
        elif storm_risk > 0.5:
            speed *= 0.4
        elif storm_risk > 0.2:
            speed *= 0.7

        # absolute floor (never zero)
        return max(speed, 2.0)


# ======================================================
# WEATHER FIELD (O(1) LOOKUPS ONLY)
# ======================================================

class WeatherField:
    def __init__(self, cache_file):
        print(f"[INFO] Loading weather cache from {cache_file}...")
        with open(cache_file, "rb") as f:
            self.data = pickle.load(f)
        print(f"[INFO] Weather cache loaded: {len(self.data):,} grid points")

    def _key(self, lat, lon):
        # MUST match cache resolution
        return (round(lat, 1), round(lon, 1))

    def wave_height(self, lat, lon):
        return self.data.get(self._key(lat, lon), {}).get("wave_height", 2.0)

    def storm_risk(self, lat, lon):
        return self.data.get(self._key(lat, lon), {}).get("storm_risk", 0.0)


# ======================================================
# WEATHER CACHE BUILDER (NO CHANGE, JUST CLEANED)
# ======================================================

def build_dummy_weather_cache(
    lat_min, lat_max, lon_min, lon_max,
    storm_center=(10.0, 85.0),
    storm_radius_km=600,
    output="weather_cache.pkl",
    resolution=1.0,
    storm_intensity_multiplier=1.0
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
    storm_points = 0
    total_points = 0

    print(f"[INFO] Generating weather cache ({resolution}° resolution)")

    for lat in range(int(lat_min), int(lat_max), step):
        for lon in range(int(lon_min), int(lon_max), step):
            lat_f = float(lat)
            lon_f = float(lon)

            wave_h = 1.5 + 1.2 * abs(math.sin(math.radians(lat_f)))

            d = haversine((lat_f, lon_f), storm_center)
            if d < storm_radius_km:
                storm_risk = max(
                    0.0,
                    min(1.0, (1.0 - d / storm_radius_km) * storm_intensity_multiplier),
                )
                wave_h += 3.0 * storm_risk
                storm_points += 1
            else:
                storm_risk = 0.0

            data[(round(lat_f, 1), round(lon_f, 1))] = {
                "wave_height": wave_h,
                "storm_risk": storm_risk,
            }
            total_points += 1

    with open(output, "wb") as f:
        pickle.dump(data, f)

    print(f"[OK] Weather cache saved → {output}")
    print(f"[OK] Grid points: {total_points:,}")
    print(f"[OK] Storm points: {storm_points:,}")
