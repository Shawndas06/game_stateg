"""Привязка координат города к суше — если точка попала в море из‑за упрощённой геометрии карты."""

from __future__ import annotations

import math


def snap_lonlat_to_land(lon: float, lat: float, step: float = 0.032, max_ring: int = 100) -> tuple[float, float]:
    """
    Если (lon, lat) не на суше, ищем ближайшую точку на суше по кольцам от исходной точки.
    """
    from src.map.geography_land import is_land

    if is_land(lon, lat):
        return lon, lat

    best: tuple[float, float] | None = None
    best_d2 = float("inf")

    for ring in range(1, max_ring):
        for deg in range(0, 360, 5):
            rad = math.radians(deg)
            dlon = math.cos(rad) * ring * step
            dlat = math.sin(rad) * ring * step
            nlon = lon + dlon
            nlat = lat + dlat
            if is_land(nlon, nlat):
                d2 = dlon * dlon + dlat * dlat
                if d2 < best_d2:
                    best_d2 = d2
                    best = (nlon, nlat)

    return best if best is not None else (lon, lat)
