#!/usr/bin/env python3
"""
Enhanced Speed Model
Calculates ship's effective speed based on real-time weather conditions:
- Wave height and period
- Wind speed and direction (relative to ship heading)
- Storm risk
"""

import math


class EnhancedSpeedModel:
    """
    Calculate effective ship speed based on weather conditions
    """
    
    def __init__(self):
        # Ship characteristics (can be customized)
        self.ship_type = "container_vessel"
        self.ship_length_m = 300  # meters
        self.draft_m = 14  # meters
        
        # Safety limits
        self.min_safe_speed_kmph = 5.0
        self.max_safe_wave_height_m = 12.0
    
    def calculate_wave_penalty(self, wave_height_m, wave_period_s=6.0):
        """
        Calculate speed reduction due to waves
        
        Significant wave height impact:
        - < 2m: minimal impact (90-100% speed)
        - 2-4m: moderate impact (70-90% speed)
        - 4-6m: significant impact (50-70% speed)
        - 6-8m: severe impact (30-50% speed)
        - > 8m: extreme impact (10-30% speed)
        
        Args:
            wave_height_m: significant wave height in meters
            wave_period_s: wave period in seconds (affects comfort/seakeeping)
        
        Returns:
            float: speed multiplier [0.1 - 1.0]
        """
        if wave_height_m < 1.0:
            return 1.0  # No penalty
        
        # Wave steepness matters too (height/period ratio)
        # Short period waves (choppy seas) are worse than long swells
        wave_steepness = wave_height_m / max(wave_period_s, 3.0)
        steepness_factor = 1.0 + (wave_steepness * 0.5)  # Amplifies penalty for steep waves
        
        # Base penalty from wave height
        if wave_height_m >= 10.0:
            penalty = 0.15  # Only 15% speed in extreme seas
        elif wave_height_m >= 8.0:
            penalty = 0.25
        elif wave_height_m >= 6.0:
            penalty = 0.40
        elif wave_height_m >= 4.0:
            penalty = 0.60
        elif wave_height_m >= 3.0:
            penalty = 0.75
        elif wave_height_m >= 2.0:
            penalty = 0.85
        else:
            # Linear interpolation for waves 1-2m
            penalty = 0.85 + (0.15 * (2.0 - wave_height_m))
        
        # Apply steepness correction
        penalty = penalty / steepness_factor
        
        return max(0.1, min(1.0, penalty))
    
    def calculate_wind_penalty(self, wind_speed_ms, wind_direction_deg, 
                               ship_heading_deg, wind_gusts_ms=None):
        """
        Calculate speed reduction due to wind
        
        Wind from ahead (headwind) causes more resistance than tailwind
        
        Args:
            wind_speed_ms: wind speed in m/s
            wind_direction_deg: direction wind is coming FROM (0-360°)
            ship_heading_deg: ship's heading (0-360°)
            wind_gusts_ms: gust speed in m/s (optional)
        
        Returns:
            float: speed multiplier [0.5 - 1.05]
        """
        # Calculate relative wind angle
        # 0° = headwind, 90° = beam wind, 180° = tailwind
        relative_angle = abs((wind_direction_deg - ship_heading_deg + 180) % 360 - 180)
        
        # Use gust speed if available and higher
        effective_wind = wind_speed_ms
        if wind_gusts_ms and wind_gusts_ms > wind_speed_ms:
            effective_wind = (wind_speed_ms + wind_gusts_ms) / 2  # Average of sustained and gust
        
        # Base wind penalty
        if effective_wind < 5.0:
            wind_factor = 1.0  # Minimal impact
        elif effective_wind < 10.0:
            wind_factor = 0.95
        elif effective_wind < 15.0:
            wind_factor = 0.90
        elif effective_wind < 20.0:
            wind_factor = 0.80
        elif effective_wind < 25.0:
            wind_factor = 0.70
        else:
            wind_factor = 0.60  # Severe wind
        
        # Directional adjustment
        # Headwind: reduce speed more
        # Tailwind: slight assistance
        angle_rad = math.radians(relative_angle)
        directional_factor = 1.0 + (0.15 * math.cos(angle_rad))  # -0.15 to +0.15
        
        final_penalty = wind_factor * directional_factor
        
        return max(0.5, min(1.05, final_penalty))
    
    def calculate_storm_penalty(self, storm_risk):
        """
        Additional penalty for being in a storm zone
        
        Args:
            storm_risk: 0.0 (calm) to 1.0 (severe storm)
        
        Returns:
            float: speed multiplier [0.2 - 1.0]
        """
        if storm_risk < 0.1:
            return 1.0
        elif storm_risk < 0.3:
            return 0.9
        elif storm_risk < 0.5:
            return 0.7
        elif storm_risk < 0.7:
            return 0.5
        elif storm_risk < 0.9:
            return 0.3
        else:
            return 0.2  # Severe storm - barely making headway
    
    def effective_speed(self, base_speed_kmph, weather_data, ship_heading_deg=0):
        """
        Calculate ship's effective speed given weather conditions
        
        Args:
            base_speed_kmph: ship's rated speed in calm conditions
            weather_data: dict with current weather (from realtime_weather)
            ship_heading_deg: ship's current heading (0-360°)
        
        Returns:
            float: effective speed in km/h
        """
        if not weather_data or 'current' not in weather_data:
            # No weather data - use base speed
            return base_speed_kmph
        
        current = weather_data['current']
        
        # Extract parameters
        wave_height = current.get('wave_height', 0)
        wave_period = current.get('wave_period', 6.0)
        wind_speed = current.get('wind_speed', 0)
        wind_direction = current.get('wind_direction', 0)
        wind_gusts = current.get('wind_gusts', 0)
        storm_risk = weather_data.get('storm_risk', 0.0)
        
        # Calculate individual penalties
        wave_multiplier = self.calculate_wave_penalty(wave_height, wave_period)
        wind_multiplier = self.calculate_wind_penalty(
            wind_speed, wind_direction, ship_heading_deg, wind_gusts
        )
        storm_multiplier = self.calculate_storm_penalty(storm_risk)
        
        # Combined effect (multiplicative)
        total_multiplier = wave_multiplier * wind_multiplier * storm_multiplier
        
        # Calculate effective speed
        effective_speed = base_speed_kmph * total_multiplier
        
        # Apply safety minimum
        effective_speed = max(self.min_safe_speed_kmph, effective_speed)
        
        return effective_speed
    
    def get_speed_breakdown(self, base_speed_kmph, weather_data, ship_heading_deg=0):
        """
        Get detailed breakdown of speed calculation
        Useful for debugging and reporting
        
        Returns:
            dict with all factors and final speed
        """
        if not weather_data or 'current' not in weather_data:
            return {
                'base_speed_kmph': base_speed_kmph,
                'effective_speed_kmph': base_speed_kmph,
                'weather_available': False
            }
        
        current = weather_data['current']
        
        wave_height = current.get('wave_height', 0)
        wave_period = current.get('wave_period', 6.0)
        wind_speed = current.get('wind_speed', 0)
        wind_direction = current.get('wind_direction', 0)
        wind_gusts = current.get('wind_gusts', 0)
        storm_risk = weather_data.get('storm_risk', 0.0)
        
        wave_mult = self.calculate_wave_penalty(wave_height, wave_period)
        wind_mult = self.calculate_wind_penalty(
            wind_speed, wind_direction, ship_heading_deg, wind_gusts
        )
        storm_mult = self.calculate_storm_penalty(storm_risk)
        
        total_mult = wave_mult * wind_mult * storm_mult
        effective = max(self.min_safe_speed_kmph, base_speed_kmph * total_mult)
        
        return {
            'base_speed_kmph': base_speed_kmph,
            'effective_speed_kmph': effective,
            'speed_reduction_pct': ((base_speed_kmph - effective) / base_speed_kmph) * 100,
            'weather_available': True,
            'conditions': {
                'wave_height_m': wave_height,
                'wave_period_s': wave_period,
                'wind_speed_ms': wind_speed,
                'wind_speed_knots': wind_speed * 1.944,
                'wind_gusts_ms': wind_gusts,
                'wind_direction': wind_direction,
                'storm_risk': storm_risk
            },
            'multipliers': {
                'wave': wave_mult,
                'wind': wind_mult,
                'storm': storm_mult,
                'total': total_mult
            }
        }


if __name__ == "__main__":
    # Test the speed model
    print("🧪 TESTING ENHANCED SPEED MODEL\n")
    
    model = EnhancedSpeedModel()
    base_speed = 35  # km/h
    
    # Test scenarios
    scenarios = [
        {
            'name': 'Calm Seas',
            'data': {
                'current': {'wave_height': 1.0, 'wave_period': 8, 'wind_speed': 5, 
                           'wind_direction': 0, 'wind_gusts': 7},
                'storm_risk': 0.0
            }
        },
        {
            'name': 'Moderate Weather',
            'data': {
                'current': {'wave_height': 3.5, 'wave_period': 6, 'wind_speed': 12, 
                           'wind_direction': 0, 'wind_gusts': 15},
                'storm_risk': 0.4
            }
        },
        {
            'name': 'Severe Storm',
            'data': {
                'current': {'wave_height': 7.0, 'wave_period': 5, 'wind_speed': 22, 
                           'wind_direction': 0, 'wind_gusts': 28},
                'storm_risk': 0.85
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{'='*60}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'='*60}")
        
        breakdown = model.get_speed_breakdown(base_speed, scenario['data'], ship_heading_deg=0)
        
        print(f"Base Speed: {breakdown['base_speed_kmph']:.1f} km/h")
        print(f"Effective Speed: {breakdown['effective_speed_kmph']:.1f} km/h")
        print(f"Reduction: {breakdown['speed_reduction_pct']:.1f}%")
        print(f"\nConditions:")
        for key, val in breakdown['conditions'].items():
            print(f"  {key}: {val:.2f}")
        print(f"\nSpeed Multipliers:")
        for key, val in breakdown['multipliers'].items():
            print(f"  {key}: {val:.3f}")
