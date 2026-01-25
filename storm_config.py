
import csv
import os

STORM_DATA_FILE = "storm_data.csv"  # Your storm data source


# ============================================================
# LOAD STORMS FROM CSV
# ============================================================
def load_storms_from_csv(filename=STORM_DATA_FILE):
    """
    Load storm data from CSV file.
    Only storms with status='active' are included.
    
    CSV Format:
    storm_id,latitude,longitude,radius_km,intensity,status,name,description
    
    Returns:
        list: [((lat, lon), radius_km, intensity), ...]
    """
    storm_centers = []
    
    if not os.path.exists(filename):
        print(f"⚠️  WARNING: {filename} not found!")
        print(f"   Creating default storm data file...")
        create_default_storm_csv(filename)
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Only load active storms
                if row['status'].strip().lower() == 'active':
                    lat = float(row['latitude'])
                    lon = float(row['longitude'])
                    radius = float(row['radius_km'])
                    intensity = float(row['intensity'])
                    
                    storm_centers.append(((lat, lon), radius, intensity))
                    
                    # Print info
                    name = row.get('name', 'Unnamed')
                    print(f"   ✓ Loaded: {name} at ({lat}°, {lon}°) - {radius}km, {intensity}x")
        
        if not storm_centers:
            print(f"   ℹ️  No active storms in {filename}")
        
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        print(f"   Using empty storm list")
        return []
    
    return storm_centers


def create_default_storm_csv(filename):
    """Create a default storm_data.csv file if it doesn't exist"""
    default_data = [
        {
            'storm_id': '1',
            'latitude': '8.0',
            'longitude': '88.0',
            'radius_km': '1000',
            'intensity': '2.0',
            'status': 'active',
            'name': 'Bay of Bengal Cyclone',
            'description': 'Large cyclone in Bay of Bengal'
        },
        {
            'storm_id': '2',
            'latitude': '12.0',
            'longitude': '82.0',
            'radius_km': '700',
            'intensity': '1.5',
            'status': 'active',
            'name': 'Arabian Sea Storm',
            'description': 'Moderate storm in Arabian Sea'
        },
        {
            'storm_id': '3',
            'latitude': '6.0',
            'longitude': '95.0',
            'radius_km': '800',
            'intensity': '2.0',
            'status': 'inactive',
            'name': 'West Sumatra Storm',
            'description': 'Inactive storm west of Sumatra'
        },
        {
            'storm_id': '4',
            'latitude': '10.0',
            'longitude': '82.0',
            'radius_km': '800',
            'intensity': '2.0',
            'status': 'inactive',
            'name': 'East Sri Lanka',
            'description': 'Inactive near Sri Lanka'
        },
        {
            'storm_id': '5',
            'latitude': '12.0',
            'longitude': '78.0',
            'radius_km': '700',
            'intensity': '1.8',
            'status': 'inactive',
            'name': 'Arabian Sea Entry',
            'description': 'Inactive Arabian Sea storm'
        }
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['storm_id', 'latitude', 'longitude', 'radius_km', 
                     'intensity', 'status', 'name', 'description']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(default_data)
    
    print(f"   ✓ Created default {filename}")


# ============================================================
# LOAD STORMS (EXECUTED AUTOMATICALLY ON IMPORT)
# ============================================================
print("\n" + "="*70)
print("LOADING STORM DATA FROM CSV")
print("="*70)
print(f"Reading: {STORM_DATA_FILE}")
print()

STORM_CENTERS = load_storms_from_csv(STORM_DATA_FILE)
STORM_PRESET = f"csv_based_{len(STORM_CENTERS)}_storms"

print()
print(f"📊 Summary: {len(STORM_CENTERS)} active storm(s) loaded")
print("="*70 + "\n")


# ============================================================
# ADVANCED SETTINGS
# ============================================================
WEATHER_RESOLUTION = 0.25  # Grid resolution in degrees
WEATHER_LAT_RANGE = (-10, 80)
WEATHER_LON_RANGE = (25, 180)
WEATHER_OUTPUT_FILE = "weather_cache.pkl"

