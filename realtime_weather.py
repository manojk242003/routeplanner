#realtime_weather.py
"""
Real-time Weather Field
Reads from realtime_weather.pkl (updated every 6 hours)
Provides weather conditions and storm risk based on actual API data
"""

import pickle
import time


class RealtimeWeatherField:
    """
    Manages real-time weather data with 6-hour cache validity
    """
    
    def __init__(self, file="realtime_weather.pkl", ttl_hours=6):
        self.file = file
        self.ttl_seconds = ttl_hours * 3600
        self.data = {}
        self._load()
    
    def _load(self):
        """Load the weather cache from pickle file"""
        try:
            with open(self.file, "rb") as f:
                self.data = pickle.load(f)
            print(f"[RT-WEATHER] Loaded {len(self.data)} weather points from {self.file}")
        except FileNotFoundError:
            print(f"⚠️  [RT-WEATHER] Cache file not found: {self.file}")
            self.data = {}
        except Exception as e:
            print(f"⚠️  [RT-WEATHER] Error loading cache: {e}")
            self.data = {}
    
    def _key(self, lat, lon):
        """Generate cache key (rounded to 0.01 degree precision)"""
        return (round(lat, 2), round(lon, 2))
    
    def is_valid(self, lat, lon):
        """Check if cached data exists and is not expired"""
        key = self._key(lat, lon)
        
        if key not in self.data:
            return False
        
        age = time.time() - self.data[key].get("timestamp", 0)
        
        if age > self.ttl_seconds:
            return False
        
        return True
    
    def reload(self):
        """Force reload the cache (call after updating realtime_weather.pkl)"""
        self._load()
    
    # ========== Weather Parameters ==========
    
    def wave_height(self, lat, lon):
        """Get current wave height in meters"""
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        current = self.data[key].get("current", {})
        return current.get("wave_height", None)
    
    def wind_speed(self, lat, lon):
        """Get current wind speed in m/s"""
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        current = self.data[key].get("current", {})
        return current.get("wind_speed", None)
    
    def wind_gusts(self, lat, lon):
        """Get wind gust speed in m/s"""
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        current = self.data[key].get("current", {})
        return current.get("wind_gusts", None)
    
    def storm_risk(self, lat, lon):
        """
        Get calculated storm risk [0.0 - 1.0]
        Based on wave height, wind speed, and gusts
        """
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        return self.data[key].get("storm_risk", 0.0)
    
    def get_full_data(self, lat, lon):
        """Get all weather data for a location"""
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        return self.data[key]
    
    def get_forecast(self, lat, lon, hours_ahead=24):
        """Get forecast data for upcoming hours"""
        if not self.is_valid(lat, lon):
            return None
        
        key = self._key(lat, lon)
        return self.data[key].get("forecast", [])
    
    def cache_age_hours(self, lat, lon):
        """Get age of cached data in hours"""
        key = self._key(lat, lon)
        
        if key not in self.data:
            return None
        
        age_seconds = time.time() - self.data[key].get("timestamp", 0)
        return age_seconds / 3600
    
    def print_summary(self, lat, lon):
        """Print weather summary for a location"""
        if not self.is_valid(lat, lon):
            print(f"⚠️  No valid weather data for ({lat:.2f}, {lon:.2f})")
            return
        
        data = self.get_full_data(lat, lon)
        current = data["current"]
        age = self.cache_age_hours(lat, lon)
        
        print(f"\n{'='*60}")
        print(f"🌊 WEATHER AT ({lat:.2f}, {lon:.2f})")
        print(f"{'='*60}")
        print(f"Data age: {age:.1f} hours")
        print(f"Storm Risk: {data['storm_risk']:.3f}")
        print(f"\nCurrent Conditions:")
        print(f"  Wave Height: {current['wave_height']:.1f} m")
        print(f"  Wave Period: {current.get('wave_period', 0):.1f} s")
        print(f"  Wind Speed: {current['wind_speed']:.1f} m/s ({current['wind_speed']*1.944:.1f} knots)")
        print(f"  Wind Gusts: {current['wind_gusts']:.1f} m/s ({current['wind_gusts']*1.944:.1f} knots)")
        print(f"  Wind Direction: {current.get('wind_direction', 0):.0f}°")
        print(f"{'='*60}\n")
