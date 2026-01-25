# fetch_realtime_storms.py (your future script)
import requests
import csv

# Get data from API
response = requests.get("https://weather-api.com/storms")
storms = response.json()

# Write to CSV
with open('storm_data.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=[...])
    writer.writeheader()
    for storm in storms:
        writer.writerow({
            'storm_id': storm['id'],
            'latitude': storm['lat'],
            'longitude': storm['lon'],
            'radius_km': storm['radius'],
            'intensity': storm['intensity'],
            'status': 'active',
            'name': storm['name'],
            'description': storm['desc']
        })

# Rebuild cache automatically
subprocess.run(["python", "build_weather_cache.py"])