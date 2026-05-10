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


def wgs84_to_epsg3857(latitude: float, longitude: float) -> tuple[float, float]:
    """Convert WGS84 latitude/longitude to Web Mercator (EPSG:3857)."""
    lat = max(min(float(latitude), 85.05112878), -85.05112878)
    lon = float(longitude)
    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return (x, y)


def polygon_centroid_wgs84_and_mercator(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """Exterior-ring centroid in EPSG:3857 and WGS84 (matches NSPD map `coordinate_x` / `coordinate_y`)."""
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
    lat, lon = epsg3857_to_4326(cx, cy)
    return (lat, lon, cx, cy)


def polygon_centroid_lat_lon(geometry: dict[str, Any]) -> tuple[float, float] | None:
    r = polygon_centroid_wgs84_and_mercator(geometry)
    return (r[0], r[1]) if r else None
