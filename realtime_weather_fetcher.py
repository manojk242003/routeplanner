# # realtime_weather_fetcher.py
#!/usr/bin/env python3
"""
Enhanced Real-time Weather Fetcher
- Fetches actual weather data from Open-Meteo API
- Calculates storm risk from wave height, wind speed, etc.
- Updates every 6 hours based on ship position
- Stores in realtime_weather.pkl (separate from static weather_cache.pkl)
"""

import requests
import pickle
import time
from datetime import datetime


REALTIME_CACHE_FILE = "realtime_weather.pkl"
CACHE_TTL_HOURS = 6
CACHE_TTL_SECONDS = CACHE_TTL_HOURS * 3600

# Storm risk calculation thresholds
STORM_THRESHOLDS = {
    'wave_height': {
        'low': 2.0,      # meters
        'moderate': 4.0,
        'high': 6.0,
        'severe': 8.0
    },
    'wind_speed': {
        'low': 10.0,     # m/s (19.4 knots)
        'moderate': 15.0, # m/s (29.1 knots)
        'high': 20.0,    # m/s (38.9 knots)
        'severe': 25.0   # m/s (48.6 knots)
    },
    'gust_speed': {
        'low': 15.0,     # m/s
        'moderate': 20.0,
        'high': 25.0,
        'severe': 30.0
    }
}


def fetch_open_meteo_marine(lat, lon, hours_ahead=24):
    """
    Fetch marine + weather data from Open-Meteo APIs
    Combines both into one unified structure
    """

    marine_url = "https://marine-api.open-meteo.com/v1/marine"
    marine_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wave_height,wave_direction,wave_period,wind_wave_height,swell_wave_height",
        "forecast_hours": hours_ahead,
        "timezone": "UTC"
    }

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
        "forecast_hours": hours_ahead,
        "timezone": "UTC"
    }

    try:
        # 🔹 CALL BOTH APIs
        marine_res = requests.get(marine_url, params=marine_params, timeout=15)
        weather_res = requests.get(weather_url, params=weather_params, timeout=15)

        marine_res.raise_for_status()
        weather_res.raise_for_status()

        marine_data = marine_res.json().get("hourly", {})
        weather_data = weather_res.json().get("hourly", {})

        # 🔹 Helper
        def safe(arr, i):
            return arr[i] if arr and i < len(arr) else 0

        # 🔹 BUILD FORECAST
        forecast_data = []
        for i in range(hours_ahead):
            forecast_data.append({
                "hour": i,
                "wave_height": safe(marine_data.get("wave_height"), i),
                "wind_speed": safe(weather_data.get("wind_speed_10m"), i),
                "wind_gusts": safe(weather_data.get("wind_gusts_10m"), i),
                "wave_period": safe(marine_data.get("wave_period"), i),
            })

        # 🔹 CURRENT DATA (index 0)
        current = {
            "wave_height": safe(marine_data.get("wave_height"), 0),
            "wave_direction": safe(marine_data.get("wave_direction"), 0),
            "wave_period": safe(marine_data.get("wave_period"), 0),
            "wind_wave_height": safe(marine_data.get("wind_wave_height"), 0),
            "swell_wave_height": safe(marine_data.get("swell_wave_height"), 0),

            "wind_speed": safe(weather_data.get("wind_speed_10m"), 0),
            "wind_direction": safe(weather_data.get("wind_direction_10m"), 0),
            "wind_gusts": safe(weather_data.get("wind_gusts_10m"), 0),
        }

        return {
            "current": current,
            "forecast": forecast_data,
            "timestamp": time.time(),
            "location": (lat, lon)
        }

    except Exception as e:
        print(f"⚠️  [RT-WEATHER] API Error at ({lat:.2f}, {lon:.2f}): {e}")
        return None

def calculate_storm_risk(weather_data):
    """
    Calculate storm risk [0.0 - 1.0] from actual weather parameters
    
    Higher risk means more dangerous conditions for shipping
    
    Args:
        weather_data: dict with wave_height, wind_speed, wind_gusts, etc.
    
    Returns:
        float: storm risk between 0.0 (calm) and 1.0 (severe storm)
    """
    if not weather_data:
        return 0.0
    
    current = weather_data.get("current", {})
    
    wave_height = current.get("wave_height", 0)
    wind_speed = current.get("wind_speed", 0)
    wind_gusts = current.get("wind_gusts", 0)
    
    # Calculate individual risk factors
    wave_risk = 0.0
    wind_risk = 0.0
    gust_risk = 0.0
    
    # Wave height risk (most important for shipping)
    if wave_height >= STORM_THRESHOLDS['wave_height']['severe']:
        wave_risk = 1.0
    elif wave_height >= STORM_THRESHOLDS['wave_height']['high']:
        wave_risk = 0.8
    elif wave_height >= STORM_THRESHOLDS['wave_height']['moderate']:
        wave_risk = 0.5
    elif wave_height >= STORM_THRESHOLDS['wave_height']['low']:
        wave_risk = 0.25
    
    # Wind speed risk
    if wind_speed >= STORM_THRESHOLDS['wind_speed']['severe']:
        wind_risk = 1.0
    elif wind_speed >= STORM_THRESHOLDS['wind_speed']['high']:
        wind_risk = 0.8
    elif wind_speed >= STORM_THRESHOLDS['wind_speed']['moderate']:
        wind_risk = 0.5
    elif wind_speed >= STORM_THRESHOLDS['wind_speed']['low']:
        wind_risk = 0.25
    
    # Wind gust risk
    if wind_gusts >= STORM_THRESHOLDS['gust_speed']['severe']:
        gust_risk = 1.0
    elif wind_gusts >= STORM_THRESHOLDS['gust_speed']['high']:
        gust_risk = 0.8
    elif wind_gusts >= STORM_THRESHOLDS['gust_speed']['moderate']:
        gust_risk = 0.5
    elif wind_gusts >= STORM_THRESHOLDS['gust_speed']['low']:
        gust_risk = 0.25
    
    # Combined storm risk (weighted average)
    # Wave height is most important (50%), wind and gusts (25% each)
    storm_risk = (0.5 * wave_risk) + (0.25 * wind_risk) + (0.25 * gust_risk)
    
    return min(1.0, storm_risk)


def build_realtime_cache(points, lookahead_hours=24):
    """
    Fetch real-time weather for a list of waypoints
    Calculate storm risk from actual weather parameters
    
    Args:
        points: list of (lat, lon) tuples - waypoints to check
        lookahead_hours: how many hours ahead to forecast
    
    Returns:
        dict: weather cache with storm risks
    """
    cache = {}
    successful = 0
    failed = 0
    
    print(f"\n{'='*70}")
    print(f"🌊 FETCHING REAL-TIME WEATHER DATA")
    print(f"{'='*70}")
    print(f"Waypoints to fetch: {len(points)}")
    print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()
    
    for i, (lat, lon) in enumerate(points, 1):
        key = (round(lat, 2), round(lon, 2))
        
        # Avoid duplicate API calls
        if key in cache:
            continue
        
        print(f"  [{i}/{len(points)}] Fetching ({lat:.2f}, {lon:.2f})...", end=" ")
        
        weather_data = fetch_open_meteo_marine(lat, lon, lookahead_hours)
        
        if weather_data:
            # Calculate storm risk from weather parameters
            storm_risk = calculate_storm_risk(weather_data)
            
            # Store complete data
            weather_data['storm_risk'] = storm_risk
            cache[key] = weather_data
            
            # Print summary
            current = weather_data['current']
            risk_label = (
                "🔴 SEVERE" if storm_risk > 0.8 else
                "🟠 HIGH" if storm_risk > 0.6 else
                "🟡 MODERATE" if storm_risk > 0.3 else
                "🟢 LOW"
            )
            
            print(f"{risk_label} (Wave: {current['wave_height']:.1f}m, Wind: {current['wind_speed']:.1f}m/s)")
            successful += 1
            
            # Rate limiting - be nice to the API
            time.sleep(0.5)
        else:
            print(f"❌ FAILED")
            failed += 1
    
    # Save to pickle file
    with open(REALTIME_CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)
    
    print()
    print(f"{'='*70}")
    print(f"✅ REAL-TIME WEATHER CACHE UPDATED")
    print(f"   File: {REALTIME_CACHE_FILE}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Cache expires in: {CACHE_TTL_HOURS} hours")
    print(f"{'='*70}\n")
    
    return cache


def get_weather_summary(lat, lon):
    """
    Get weather summary for a specific location from cache
    """
    try:
        with open(REALTIME_CACHE_FILE, "rb") as f:
            cache = pickle.load(f)
        
        key = (round(lat, 2), round(lon, 2))
        
        if key in cache:
            data = cache[key]
            age_hours = (time.time() - data['timestamp']) / 3600
            
            if age_hours < CACHE_TTL_HOURS:
                return data
            else:
                print(f"⚠️  Weather data for {key} is {age_hours:.1f} hours old (stale)")
                return None
        else:
            return None
            
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    # Test the real-time weather fetcher
    print("🧪 TESTING REAL-TIME WEATHER FETCHER\n")
    
    # Test points along Mumbai-Singapore route
    test_points = [
        (18.9, 72.8),   # Mumbai
        (15.0, 75.0),   # Arabian Sea
        (10.0, 80.0),   # Bay of Bengal
        (5.0, 90.0),    # Near Andaman
        (1.3, 103.8),   # Singapore
    ]
    
    cache = build_realtime_cache(test_points, lookahead_hours=24)
    
    print("\n📊 WEATHER SUMMARY:")
    for point in test_points:
        key = (round(point[0], 2), round(point[1], 2))
        if key in cache:
            data = cache[key]
            current = data['current']
            print(f"\n{point}:")
            print(f"  Storm Risk: {data['storm_risk']:.3f}")
            print(f"  Wave Height: {current['wave_height']:.1f}m")
            print(f"  Wind Speed: {current['wind_speed']:.1f}m/s")
            print(f"  Wind Gusts: {current['wind_gusts']:.1f}m/s")
