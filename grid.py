# grid.py

from config import GRID_RESOLUTION

def snap_to_grid(coord):
    lat, lon = coord
    return (
        round(lat / GRID_RESOLUTION) * GRID_RESOLUTION,
        round(lon / GRID_RESOLUTION) * GRID_RESOLUTION,
    )

def get_neighbors(node):
    lat, lon = node
    step = GRID_RESOLUTION

    neighbors = []
    for dlat in (-step, 0, step):
        for dlon in (-step, 0, step):
            if dlat == 0 and dlon == 0:
                continue
            new_lat = round((lat + dlat) / step) * step
            new_lon = round((lon + dlon) / step) * step
            
            # Wrap longitude around 0-360
            new_lon = new_lon % 360.0
            
            n = (new_lat, new_lon)
            neighbors.append(n)
    return neighbors
