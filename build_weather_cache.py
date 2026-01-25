#--------------------------

#!/usr/bin/env python3
"""
Builds weather cache from storm_config.py settings
Just run: python build_weather_cache.py
"""

import pickle
import math
from storm_config import (
    STORM_PRESET,
    STORM_CENTERS,
    WEATHER_RESOLUTION,
    WEATHER_LAT_RANGE,
    WEATHER_LON_RANGE,
    WEATHER_OUTPUT_FILE
)


def haversine(a, b):
    """Calculate distance between two lat/lon points in km"""
    R = 6371
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(h))


def build_weather_cache():
    """Build weather cache using configuration from storm_config.py"""
    
    LAT_MIN, LAT_MAX = WEATHER_LAT_RANGE
    LON_MIN, LON_MAX = WEATHER_LON_RANGE
    
    print("="*70)
    print("BUILDING WEATHER CACHE")
    print("="*70)
    print(f"Preset: {STORM_PRESET}")
    print(f"Resolution: {WEATHER_RESOLUTION}°")
    
    if STORM_CENTERS:
        print(f"Storm centers: {len(STORM_CENTERS)}")
        for i, (center, radius, intensity) in enumerate(STORM_CENTERS, 1):
            print(f"  {i}. {center} - Radius: {radius}km, Intensity: {intensity}x")
    else:
        print("Storm centers: NONE (Clear weather)")
    print()
    
    data = {}
    storm_points = 0
    max_intensity = 0.0
    
    # Generate grid
    lat_range = [LAT_MIN + i * WEATHER_RESOLUTION 
                 for i in range(int((LAT_MAX - LAT_MIN) / WEATHER_RESOLUTION))]
    lon_range = [LON_MIN + i * WEATHER_RESOLUTION 
                 for i in range(int((LON_MAX - LON_MIN) / WEATHER_RESOLUTION))]
    
    total = 0
    
    for lat_f in lat_range:
        for lon_f in lon_range:
            # Base wave conditions
            wave_h = 1.5 + 1.2 * abs(math.sin(math.radians(lat_f)))
            wave_dir = (lon_f * 2) % 360
            storm_risk = 0.0
            
            # Calculate storm influence from all centers
            for center, radius_km, intensity in STORM_CENTERS:
                d = haversine((lat_f, lon_f), center)
                
                if d < radius_km:
                    # Quadratic falloff from center
                    normalized_dist = d / radius_km
                    risk = (1.0 - normalized_dist ** 2) * intensity
                    risk = max(0.0, min(1.0, risk))
                    
                    # Take maximum storm risk if multiple storms overlap
                    storm_risk = max(storm_risk, risk)
            
            if storm_risk > 0.1:
                storm_points += 1
                max_intensity = max(max_intensity, storm_risk)
                # Add extra waves in storm areas
                wave_h += 5.0 * storm_risk
            
            # Store with 0.1 degree precision for lookup
            key = (round(lat_f, 1), round(lon_f, 1))
            
            # Keep maximum storm risk if key already exists
            if key in data:
                existing_risk = data[key]["storm_risk"]
                if storm_risk > existing_risk:
                    data[key] = {
                        "wave_height": wave_h,
                        "wave_dir": wave_dir,
                        "storm_risk": storm_risk,
                    }
            else:
                data[key] = {
                    "wave_height": wave_h,
                    "wave_dir": wave_dir,
                    "storm_risk": storm_risk,
                }
            
            total += 1
    
    # Save to file
    with open(WEATHER_OUTPUT_FILE, "wb") as f:
        pickle.dump(data, f)
    
    import os
    file_size_kb = os.path.getsize(WEATHER_OUTPUT_FILE) / 1024
    
    print(f"✅ WEATHER CACHE BUILT!")
    print(f"   File: {WEATHER_OUTPUT_FILE}")
    print(f"   Total grid points: {len(data):,}")
    
    if STORM_CENTERS:
        print(f"   Storm-affected: {storm_points:,} ({100*storm_points/total:.1f}%)")
        print(f"   Max storm intensity: {max_intensity:.3f}")
    else:
        print(f"   Storm-affected: 0 (CLEAR WEATHER)")
    
    print(f"   File size: {file_size_kb:.1f} KB")
    print()
    print("="*70)
    print("✅ Done! Now run: python main.py")
    print("="*70)


if __name__ == "__main__":
    build_weather_cache()