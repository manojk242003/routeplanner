import xarray as xr

class Bathymetry:
    def __init__(self, nc_path: str):
        self.ds = xr.open_dataset(nc_path)
        self.depth = self.ds["elevation"]  # meters

    def is_safe(self, lat: float, lon: float, draft: float) -> bool:
        """
        Safe if ocean depth >= draft + safety margin
        """
        d = float(self.depth.sel(lat=lat, lon=lon, method="nearest"))
        return d < -(draft + 5)  # negative = ocean depth
