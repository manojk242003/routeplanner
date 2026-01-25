#!/usr/bin/env python3
"""
Debug script to check what's actually in the weather cache
"""

import pickle

def check_weather_cache(filename="weather_cache.pkl"):
    print("="*60)
    print(f"CHECKING: {filename}")
    print("="*60)
    
    try:
        with open(filename, "rb") as f:
            data = pickle.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return
    
    print(f"\n📊 Total grid points: {len(data):,}")
    
    # Check storm distribution
    storm_counts = {
        "no_storm": 0,
        "light_0.1_0.3": 0,
        "moderate_0.3_0.5": 0,
        "severe_0.5_0.8": 0,
        "extreme_0.8_1.0": 0
    }
    
    max_storm = 0.0
    max_storm_location = None
    storm_locations = []
    
    for (lat, lon), values in data.items():
        storm_risk = values.get("storm_risk", 0.0)
        
        if storm_risk > max_storm:
            max_storm = storm_risk
            max_storm_location = (lat, lon)
        
        if storm_risk == 0.0:
            storm_counts["no_storm"] += 1
        elif storm_risk < 0.3:
            storm_counts["light_0.1_0.3"] += 1
            storm_locations.append((lat, lon, storm_risk))
        elif storm_risk < 0.5:
            storm_counts["moderate_0.3_0.5"] += 1
            storm_locations.append((lat, lon, storm_risk))
        elif storm_risk < 0.8:
            storm_counts["severe_0.5_0.8"] += 1
            storm_locations.append((lat, lon, storm_risk))
        else:
            storm_counts["extreme_0.8_1.0"] += 1
            storm_locations.append((lat, lon, storm_risk))
    
    print("\n🌪️  STORM DISTRIBUTION:")
    print(f"   No storm (0.0):           {storm_counts['no_storm']:,} points")
    print(f"   Light (0.1-0.3):          {storm_counts['light_0.1_0.3']:,} points")
    print(f"   Moderate (0.3-0.5):       {storm_counts['moderate_0.3_0.5']:,} points")
    print(f"   Severe (0.5-0.8):         {storm_counts['severe_0.5_0.8']:,} points")
    print(f"   Extreme (0.8-1.0):        {storm_counts['extreme_0.8_1.0']:,} points")
    
    total_storm = len(data) - storm_counts["no_storm"]
    print(f"\n   Total storm-affected:     {total_storm:,} points ({100*total_storm/len(data):.1f}%)")
    
    if max_storm > 0:
        print(f"\n⚡ MAX STORM:")
        print(f"   Intensity: {max_storm:.3f}")
        print(f"   Location: {max_storm_location}")
        
        # Show storm center region
        if storm_locations:
            print(f"\n📍 STORM HOTSPOTS (Top 10 most intense):")
            storm_locations.sort(key=lambda x: x[2], reverse=True)
            for i, (lat, lon, risk) in enumerate(storm_locations[:10], 1):
                print(f"   {i}. ({lat:.1f}, {lon:.1f}) - Risk: {risk:.3f}")
    else:
        print("\n⚠️  WARNING: NO STORM DATA FOUND IN CACHE!")
        print("   The cache has zero storm risk everywhere.")
    
    # Check along Singapore-Mumbai route
    print(f"\n🚢 STORM ALONG SINGAPORE-MUMBAI ROUTE:")
    route_points = [
        (1.0, 104.0, "Singapore"),
        (5.0, 95.0, "West of Sumatra"),
        (8.0, 82.0, "Sri Lanka area"),
        (10.0, 75.0, "Arabian Sea"),
        (15.0, 70.0, "Near Mumbai"),
        (19.0, 73.0, "Mumbai")
    ]
    
    for lat, lon, name in route_points:
        key = (round(lat, 1), round(lon, 1))
        if key in data:
            storm = data[key].get("storm_risk", 0.0)
            wave = data[key].get("wave_height", 0.0)
            print(f"   {name:20s} ({lat:.1f}, {lon:.1f}): Storm={storm:.3f}, Wave={wave:.1f}m")
        else:
            print(f"   {name:20s} ({lat:.1f}, {lon:.1f}): NOT IN CACHE")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    check_weather_cache("weather_cache.pkl")