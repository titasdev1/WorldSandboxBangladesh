"""Geographic tile-grid helpers shared by the map builder and offline tests."""
from __future__ import annotations

from collections.abc import Iterator


def tile_bounds(
    region: tuple[float, float, float, float],
    tile_degrees: float,
) -> Iterator[tuple[float, float, float, float]]:
    """Yield row-major (south, west, north, east) bounds covering a region."""
    south, west, north, east = region
    lat = south
    while lat < north - 1e-9:
        next_lat = min(north, lat + tile_degrees)
        lon = west
        while lon < east - 1e-9:
            next_lon = min(east, lon + tile_degrees)
            yield (round(lat, 7), round(lon, 7), round(next_lat, 7), round(next_lon, 7))
            lon = next_lon
        lat = next_lat
