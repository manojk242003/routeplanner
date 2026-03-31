#!/usr/bin/env python3
"""
Hybrid Weather System
- Tries to fetch real-time weather from API
- Falls back to static weather cache if API fails
- Ensures storm detection always works
"""

import pickle
import time
from datetime import datetime
try:
    from realtime_weather_fetcher_v2 import fetch_open_meteo_marine, calculate_storm_risk
    API_AVAILABLE = True
except:
    API_AVAILABLE = False
    # print("⚠️  Real-time weather fetcher not available")


REALTIME_CACHE_FILE = "realtime_weather.pkl"
STATIC_CACHE_FILE = "weather_cache.pkl"
CACHE_TTL_HOURS = 6
CACHE_TTL_SECONDS = CACHE_TTL_HOURS * 3600


class HybridWeatherField:
    """
    Weather system that combines real-time API and static cache
    - Attempts real-time fetch first
    - Falls back to static weather if API unavailable
    - Always provides weather data for storm detection
    """
    
    def __init__(self, realtime_file=REALTIME_CACHE_FILE, static_file=STATIC_CACHE_FILE):
        self.realtime_file = realtime_file
        self.static_file = static_file
        self.realtime_data = {}
        self.static_data = {}
        
        # Load both caches
        self._load_realtime()
        self._load_static()
        
        print(f"\n{'='*70}")
        print(f"🌦️  HYBRID WEATHER SYSTEM INITIALIZED")
        print(f"{'='*70}")
        # print(f"Real-time cache: {len(self.realtime_data)} points")
        # print(f"Static cache: {len(self.static_data)} points")
        print(f"{'='*70}\n")
    
    def _load_realtime(self):
        """Load real-time weather cache"""
        try:
            with open(self.realtime_file, "rb") as f:
                self.realtime_data = pickle.load(f)
        except FileNotFoundError:
            self.realtime_data = {}
        except Exception as e:
            print(f"⚠️  Error loading real-time cache: {e}")
            self.realtime_data = {}
    
    def _load_static(self):
        """Load static weather cache"""
        try:
            with open(self.static_file, "rb") as f:
                self.static_data = pickle.load(f)
        except FileNotFoundError:
            print(f"⚠️  Static weather cache not found: {self.static_file}")
            self.static_data = {}
        except Exception as e:
            print(f"⚠️  Error loading static cache: {e}")
            self.static_data = {}
    
    def _key_realtime(self, lat, lon):
        """Key for real-time cache (0.01° precision)"""
        return (round(lat, 2), round(lon, 2))
    
    def _key_static(self, lat, lon):
        """Key for static cache (0.1° precision)"""
        return (round(lat, 1), round(lon, 1))
    
    def reload(self):
        """Reload both caches"""
        self._load_realtime()
        self._load_static()
    
    def is_realtime_valid(self, lat, lon):
        """Check if real-time data exists and is not expired"""
        key = self._key_realtime(lat, lon)
        
        if key not in self.realtime_data:
            return False
        
        data = self.realtime_data[key]
        
        # Check if it's a dict with timestamp
        if not isinstance(data, dict) or 'timestamp' not in data:
            return False
        
        age = time.time() - data.get("timestamp", 0)
        
        return age <= CACHE_TTL_SECONDS
    
    def get_weather_data(self, lat, lon):
        """
        Get weather data - tries real-time first, falls back to static
        
        Returns:
            dict with weather data or None
        """
        # Try real-time first
        if self.is_realtime_valid(lat, lon):
            key = self._key_realtime(lat, lon)
            return self.realtime_data[key]
        
        # Fall back to static
        key_static = self._key_static(lat, lon)
        if key_static in self.static_data:
            static = self.static_data[key_static]
            
            # Convert static format to unified format
            return {
                'current': {
                    'wave_height': static.get('wave_height', 2.0),
                    'wave_period': 6.0,
                    'wind_speed': 10.0,
                    'wind_direction': 0,
                    'wind_gusts': 12.0,
                },
                'storm_risk': static.get('storm_risk', 0.0),
                'timestamp': time.time(),
                'source': 'static'
            }
        
        # No data available
        return None
    
    def get_full_data(self, lat, lon):
        """Alias for get_weather_data"""
        return self.get_weather_data(lat, lon)
    
    def storm_risk(self, lat, lon):
        """Get storm risk [0.0 - 1.0]"""
        data = self.get_weather_data(lat, lon)
        if data:
            return data.get('storm_risk', 0.0)
        return 0.0
    
    def wave_height(self, lat, lon):
        """Get wave height in meters"""
        data = self.get_weather_data(lat, lon)
        if data and 'current' in data:
            return data['current'].get('wave_height', 2.0)
        return 2.0
    
    def wind_speed(self, lat, lon):
        """Get wind speed in m/s"""
        data = self.get_weather_data(lat, lon)
        if data and 'current' in data:
            return data['current'].get('wind_speed', 10.0)
        return 10.0
    
    def wind_gusts(self, lat, lon):
        """Get wind gust speed in m/s"""
        data = self.get_weather_data(lat, lon)
        if data and 'current' in data:
            return data['current'].get('wind_gusts', 12.0)
        return 12.0
    
    def print_summary(self, lat, lon):
        """Print weather summary"""
        data = self.get_weather_data(lat, lon)
        
        if not data:
            print(f"⚠️  No weather data available for ({lat:.2f}, {lon:.2f})")
            return
        
        source = data.get('source', 'real-time')
        current = data.get('current', {})
        storm_risk = data.get('storm_risk', 0.0)
        
        print(f"\n{'='*60}")
        print(f"🌊 WEATHER AT ({lat:.2f}, {lon:.2f})")
        print(f"{'='*60}")
        print(f"Source: {source.upper()}")
        print(f"Storm Risk: {storm_risk:.3f}")
        print(f"\nConditions:")
        print(f"  Wave Height: {current.get('wave_height', 0):.1f} m")
        print(f"  Wind Speed: {current.get('wind_speed', 0):.1f} m/s")
        print(f"  Wind Gusts: {current.get('wind_gusts', 0):.1f} m/s")
        print(f"{'='*60}\n")


def build_hybrid_weather_cache(points, lookahead_hours=24):
    """
    Attempt to fetch real-time weather, but don't fail if API unavailable
    """
    if not API_AVAILABLE:
        # print("⚠️  Real-time API not available - using static weather only")
        return {}
    
    cache = {}
    successful = 0
    failed = 0
    
    print(f"\n{'='*70}")
    print(f"🌊 ATTEMPTING REAL-TIME WEATHER FETCH")
    print(f"{'='*70}")
    print(f"Waypoints: {len(points)}")
    print(f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()
    
    for i, (lat, lon) in enumerate(points, 1):
        key = (round(lat, 2), round(lon, 2))
        
        if key in cache:
            continue
        
        print(f"  [{i}/{len(points)}] ({lat:.2f}, {lon:.2f})...", end=" ")
        
        try:
            weather_data = fetch_open_meteo_marine(lat, lon, lookahead_hours)
            
            if weather_data:
                storm_risk = calculate_storm_risk(weather_data)
                weather_data['storm_risk'] = storm_risk
                cache[key] = weather_data
                
                print(f"✓ Risk: {storm_risk:.2f}")
                successful += 1
                time.sleep(0.5)  # Rate limiting
            else:
                print("❌ No data")
                failed += 1
                
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            failed += 1
    
    # Save cache
    if cache:
        with open(REALTIME_CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)
        print(f"\n✅ Saved {successful} weather points to {REALTIME_CACHE_FILE}")
    else:
        print(f"\n⚠️  No real-time data fetched - will use static weather")
    
    print(f"   Successful: {successful} | Failed: {failed}")
    print(f"{'='*70}\n")
    
    return cache


if __name__ == "__main__":
    print("🧪 TESTING HYBRID WEATHER SYSTEM\n")
    
    # Test points
    test_points = [
        (18.9, 72.8),   # Mumbai
        (10.0, 80.0),   # Bay of Bengal
        (1.3, 103.8),   # Singapore
    ]
    
    # Try to fetch real-time weather
    build_hybrid_weather_cache(test_points)
    
    # Test the hybrid system
    weather = HybridWeatherField()
    
    for lat, lon in test_points:
        weather.print_summary(lat, lon)
