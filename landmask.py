from functools import lru_cache
import geopandas as gpd
from shapely.geometry import Point

class LandMask:
    def __init__(self, shapefile_path):
        self.land = gpd.read_file(shapefile_path).to_crs(epsg=4326)
        self.land_union = self.land.unary_union

    @lru_cache(maxsize=500_000)
    def is_ocean(self, lat, lon):
        point = Point(lon, lat)
        return not self.land_union.contains(point)
