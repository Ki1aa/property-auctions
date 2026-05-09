"""EPSG:3857 (Web Mercator) helpers for NSPD GeoJSON polygons."""

from __future__ import annotations

import math
from typing import Any


def epsg3857_to_4326(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator to WGS84. Returns (latitude, longitude)."""
    lon = (x / 20037508.34) * 180.0
    lat = (y / 20037508.34) * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return (lat, lon)


def polygon_centroid_lat_lon(geometry: dict[str, Any]) -> tuple[float, float] | None:
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        return None
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return None
    ring = coords[0]
    if not isinstance(ring, list) or len(ring) < 3:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for pt in ring:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        xs.append(float(pt[0]))
        ys.append(float(pt[1]))
    if len(xs) < 3:
        return None
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    return epsg3857_to_4326(cx, cy)
