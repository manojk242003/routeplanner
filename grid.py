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
            n = (
                round((lat + dlat) / step) * step,
                round((lon + dlon) / step) * step,
            )
            neighbors.append(n)
    return neighbors
