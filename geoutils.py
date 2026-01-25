# geo.py

from math import radians, sin, cos, sqrt, atan2
from config import EARTH_RADIUS_KM

def haversine(a, b):
    lat1, lon1 = map(radians, a)
    lat2, lon2 = map(radians, b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    h = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(h), sqrt(1 - h))
