"""GIS Torgi + NSPD + Domclick URLs for MVP lots."""

from __future__ import annotations

from math import cos, radians
from urllib.parse import quote, urlencode

from app.config import settings


def build_notice_url(notice_number: str) -> str:
    nn = str(notice_number).strip()
    return f"https://torgi.gov.ru/new/public/notices/view/{quote(nn, safe='')}"


def build_lot_url(notice_number: str, lot_number: str | int) -> str:
    nn = str(notice_number).strip()
    ln = str(lot_number).strip()
    lot_code = quote(f"{nn}_{ln}", safe="_")
    return f"https://torgi.gov.ru/new/public/lots/lot/{lot_code}/(lotInfo:info)"


def build_nspd_search_url(cadastral_number: str) -> str:
    cad = (cadastral_number or "").strip()
    if not cad:
        return ""
    params = {
        "thematic": "PKK",
        "theme_id": "1",
        "baseLayerId": "235",
        "is_copy_url": "true",
        "query": cad,
    }
    return "https://nspd.gov.ru/map?" + urlencode(params)


def _normalize_torgi_https(url: str | None) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    if u.startswith("http://torgi.gov.ru"):
        return "https://" + u[len("http://") :]
    if u.startswith("/new/"):
        return "https://torgi.gov.ru" + u
    return u


def resolve_notice_href_from_raw(raw: dict | None) -> str | None:
    if not isinstance(raw, dict):
        return None
    for key in ("href",):
        v = raw.get(key)
        if isinstance(v, str) and ("torgi.gov.ru" in v or v.startswith("/new/")):
            return _normalize_torgi_https(v)
    export_object = raw.get("exportObject")
    if isinstance(export_object, dict):
        structured = export_object.get("structuredObject")
        if isinstance(structured, dict):
            notice = structured.get("notice")
            if isinstance(notice, dict):
                common = notice.get("commonInfo")
                if isinstance(common, dict):
                    h = common.get("href")
                    if isinstance(h, str):
                        return _normalize_torgi_https(h)
    common_info = raw.get("commonInfo")
    if isinstance(common_info, dict):
        h = common_info.get("href")
        if isinstance(h, str):
            return _normalize_torgi_https(h)
    return None


def _bbox_around_wgs84(latitude: float, longitude: float, radius_km: float) -> tuple[float, float, float, float]:
    radius = max(float(radius_km or 0), 0.1)
    lat_delta = radius / 111.32
    lon_scale = max(cos(radians(latitude)), 0.2)
    lon_delta = radius / (111.32 * lon_scale)
    south = max(latitude - lat_delta, -90)
    north = min(latitude + lat_delta, 90)
    west = max(longitude - lon_delta, -180)
    east = min(longitude + lon_delta, 180)
    return south, west, north, east


def _fmt_coord_bbox(value: float) -> str:
    s = f"{float(value):.14f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def build_domclick_map_url(lat: float | None, lon: float | None) -> str | None:
    if lat is None or lon is None:
        return None
    if not settings.include_marketplace_map_urls:
        return None
    lat_f, lon_f = float(lat), float(lon)
    south, west, north, east = _bbox_around_wgs84(lat_f, lon_f, settings.marketplace_map_radius_km)
    params: dict[str, str] = {
        "deal_type": "sale",
        "category": "living",
        "offer_type": "lot",
        "sw": f"{_fmt_coord_bbox(south)},{_fmt_coord_bbox(west)}",
        "ne": f"{_fmt_coord_bbox(north)},{_fmt_coord_bbox(east)}",
        "offset": "0",
    }
    aids = (settings.domclick_on_map_aids or "").strip()
    if aids:
        params["aids"] = aids
    base = (settings.domclick_on_map_base_url or "").strip().rstrip("/") or "https://domclick.ru/search/on-map"
    return f"{base}?" + urlencode(params, safe=",")
