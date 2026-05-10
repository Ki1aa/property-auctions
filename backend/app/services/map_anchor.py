"""Canonical map coordinates for a lot (NSPD polygon centroid vs notice lat/lon)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Lot


def _valid_lat_lon(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if latitude is None or longitude is None:
        return None
    lat = float(latitude)
    lon = float(longitude)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def refresh_lot_map_anchor(lot: Lot) -> None:
    """Set map_anchor_* from NSPD centroid when present, else notice coordinates."""
    nspd = _valid_lat_lon(lot.nspd_centroid_latitude, lot.nspd_centroid_longitude)
    notice = _valid_lat_lon(lot.latitude, lot.longitude)
    now = datetime.now(timezone.utc)
    if nspd is not None:
        lot.map_anchor_latitude, lot.map_anchor_longitude = nspd
        lot.map_anchor_source = "nspd_polygon"
        lot.map_anchor_updated_at = now
    elif notice is not None:
        lot.map_anchor_latitude, lot.map_anchor_longitude = notice
        lot.map_anchor_source = "notice"
        lot.map_anchor_updated_at = now
    else:
        lot.map_anchor_latitude = None
        lot.map_anchor_longitude = None
        lot.map_anchor_source = None
        lot.map_anchor_updated_at = now


def lot_map_display_coordinates(lot: Lot) -> tuple[float, float] | None:
    """WGS84 point for maps and marketplace bbox; anchor first, then legacy fallbacks."""
    anchor = _valid_lat_lon(lot.map_anchor_latitude, lot.map_anchor_longitude)
    if anchor is not None:
        return anchor
    return _valid_lat_lon(lot.nspd_centroid_latitude, lot.nspd_centroid_longitude) or _valid_lat_lon(
        lot.latitude,
        lot.longitude,
    )


def lot_has_map_centroid(lot: Lot) -> bool:
    return lot_map_display_coordinates(lot) is not None
