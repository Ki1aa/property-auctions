"""Deep links for lots: GIS Torgi, NSPD map, app SPA, marketplace search."""

from __future__ import annotations

import re
from math import cos, radians
from urllib.parse import quote, urlencode

from app.config import settings
from app.models import Lot
from app.services.nspd.geometry import wgs84_to_epsg3857

TORGI_NOTICE_VIEW = "https://torgi.gov.ru/new/public/notices/view/{notice_number}"
NSPD_PUBLIC_MAP_URL = "https://nspd.gov.ru/map?thematic=PKK"
NSPD_MAP_BASE_PARAMS = {
    "thematic": "PKK",
    "theme_id": "1",
    "baseLayerId": "235",
    "is_copy_url": "true",
}
DOMCLICK_HOST_BY_REGION = {
    "72": "tyumen.domclick.ru",
    "86": "xanty-mansijsk.domclick.ru",
    "89": "salekhard.domclick.ru",
}


def _notice_reg_number(lot: Lot, notice_payload: dict | None) -> str | None:
    if notice_payload:
        for key in ("regNum", "noticeNumber", "reg_num"):
            raw = notice_payload.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
        common_info = notice_payload.get("commonInfo")
        if isinstance(common_info, dict):
            raw = common_info.get("noticeNumber")
            if raw is not None and str(raw).strip():
                return str(raw).strip()
    sid = (lot.source_id or "").strip()
    if not sid or sid.lower().startswith("http"):
        return None
    if len(sid) >= 10 and re.fullmatch(r"\d+", sid):
        return sid
    multi_lot_match = re.fullmatch(r"(\d{10,}):lot:.+", sid)
    if multi_lot_match:
        return multi_lot_match.group(1)
    return None


def _official_notice_href(notice_payload: dict | None) -> str | None:
    """Official HTML href from Torgi notice detail JSON, when present."""
    if not notice_payload:
        return None
    candidates: list[object] = [notice_payload.get("href")]
    export_object = notice_payload.get("exportObject")
    if isinstance(export_object, dict):
        structured = export_object.get("structuredObject")
        if isinstance(structured, dict):
            notice = structured.get("notice")
            if isinstance(notice, dict):
                common_info = notice.get("commonInfo")
                if isinstance(common_info, dict):
                    candidates.append(common_info.get("href"))
    common_info = notice_payload.get("commonInfo")
    if isinstance(common_info, dict):
        candidates.append(common_info.get("href"))

    for raw in candidates:
        href = str(raw or "").strip()
        if href.startswith("https://torgi.gov.ru/new/public/notices/view/"):
            return href
        if href.startswith("/new/public/notices/view/"):
            return f"https://torgi.gov.ru{href}"
    return None


def torgi_notice_json_url(lot: Lot) -> str | None:
    """OpenData / notice detail JSON URL (href)."""
    return (lot.notice_detail_url or lot.source_url or "").strip() or None


def torgi_notice_html_url(lot: Lot, notice_payload: dict | None = None) -> str | None:
    """Official SPA notice card on torgi.gov.ru when registry number is known."""
    official_href = _official_notice_href(notice_payload)
    if official_href:
        return official_href
    reg = _notice_reg_number(lot, notice_payload)
    if not reg:
        return None
    return TORGI_NOTICE_VIEW.format(notice_number=quote(reg, safe=""))


def torgi_public_url(lot: Lot, notice_payload: dict | None = None) -> str | None:
    """Prefer human-readable notice page; fall back to JSON notice URL."""
    return torgi_notice_html_url(lot, notice_payload) or torgi_notice_json_url(lot)


def torgi_notice_json_link_when_distinct(lot: Lot, notice_payload: dict | None = None) -> str | None:
    """Second link for UI/Telegram: raw JSON href when it differs from the HTML card URL."""
    html_u = (torgi_notice_html_url(lot, notice_payload) or "").strip().rstrip("/")
    json_u = (torgi_notice_json_url(lot) or "").strip().rstrip("/")
    if not json_u:
        return None
    if html_u and json_u != html_u:
        return json_u.strip() or None
    return None


def pkk_map_url(cadastral_number: str | None) -> str | None:
    """Legacy PKK deep links are intentionally disabled: the service is no longer reliable."""
    return None


def nspd_map_url(
    cadastral_number: str | None,
    *,
    centroid_latitude: float | None = None,
    centroid_longitude: float | None = None,
    card_id: str | None = None,
    card_type: str | None = None,
) -> str | None:
    """Best-effort NSPD deep link; fallback keeps cadastral number in the URL query."""
    cad = (cadastral_number or "").strip()
    if not cad:
        return None
    params: dict[str, str] = dict(NSPD_MAP_BASE_PARAMS)
    card_id_s = (card_id or "").strip()
    card_type_s = (card_type or "").strip()
    if centroid_latitude is not None and centroid_longitude is not None:
        x, y = wgs84_to_epsg3857(centroid_latitude, centroid_longitude)
        params.update(
            {
                "zoom": "20",
                "coordinate_x": str(x),
                "coordinate_y": str(y),
            }
        )
    if card_id_s and card_type_s and centroid_latitude is not None and centroid_longitude is not None:
        params["selectedCard"] = f"{card_id_s},{card_type_s},{cad}"
    else:
        params["query"] = cad
    return "https://nspd.gov.ru/map?" + urlencode(params, safe=":,")


def nspd_lot_map_url(lot: Lot) -> str | None:
    return nspd_map_url(
        lot.cadastral_number,
        centroid_latitude=lot.nspd_centroid_latitude,
        centroid_longitude=lot.nspd_centroid_longitude,
        card_id=lot.nspd_card_id,
        card_type=lot.nspd_card_type,
    )


def app_public_lot_url(lot_id: int) -> str | None:
    base = (settings.app_public_base_url or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}/lots/{lot_id}"


def _marketplace_search_query_full(lot: Lot) -> str:
    parts = [
        lot.cadastral_number,
        lot.address,
        lot.municipality,
        lot.settlement,
        lot.region,
    ]
    return ", ".join(str(p).strip() for p in parts if p and str(p).strip())


def _marketplace_search_query_cadastral_only(lot: Lot) -> str | None:
    c = (lot.cadastral_number or "").strip()
    return c or None


def _marketplace_url_from_template(template: str, query: str | None) -> str | None:
    if not settings.include_marketplace_search_urls:
        return None
    q = (query or "").strip()
    if not q:
        return None
    t = (template or "").strip()
    if not t:
        return None
    enc = quote(q, safe="")
    return t.format(q=enc)


def _valid_lat_lon(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if latitude is None or longitude is None:
        return None
    lat = float(latitude)
    lon = float(longitude)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _lot_marketplace_centroid(lot: Lot) -> tuple[float, float] | None:
    return _valid_lat_lon(
        lot.nspd_centroid_latitude,
        lot.nspd_centroid_longitude,
    ) or _valid_lat_lon(lot.latitude, lot.longitude)


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


def _fmt_coord(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def domclick_land_map_url(lot: Lot) -> str | None:
    """Best-effort Domclick map search around lot coordinates; useful for manual analog lookup."""
    if not settings.include_marketplace_map_urls:
        return None
    centroid = _lot_marketplace_centroid(lot)
    if centroid is None:
        return None
    lat, lon = centroid
    south, west, north, east = _bbox_around_wgs84(lat, lon, settings.marketplace_map_radius_km)
    host = DOMCLICK_HOST_BY_REGION.get(str(lot.region or "").strip(), "domclick.ru")
    params = {
        "deal_type": "sale",
        "category": "living",
        "offer_type": "lot",
        "sw": f"{_fmt_coord(south)},{_fmt_coord(west)}",
        "ne": f"{_fmt_coord(north)},{_fmt_coord(east)}",
        "offset": "0",
    }
    return f"https://{host}/search/on-map?" + urlencode(params, safe=",")


def domclick_land_search_url(lot: Lot) -> str | None:
    """Best-effort Domclick search; not a cadastral deep link."""
    return _marketplace_url_from_template(
        settings.domclick_search_template, _marketplace_search_query_full(lot)
    )


def domclick_land_search_url_cadastral_only(lot: Lot) -> str | None:
    return _marketplace_url_from_template(
        settings.domclick_search_template, _marketplace_search_query_cadastral_only(lot)
    )


def avito_search_url(lot: Lot) -> str | None:
    """Best-effort Avito search for land listings."""
    return _marketplace_url_from_template(
        settings.avito_land_search_template, _marketplace_search_query_full(lot)
    )


def avito_search_url_cadastral_only(lot: Lot) -> str | None:
    return _marketplace_url_from_template(
        settings.avito_land_search_template, _marketplace_search_query_cadastral_only(lot)
    )


def cian_land_search_url(lot: Lot) -> str | None:
    return _marketplace_url_from_template(
        settings.cian_land_search_template, _marketplace_search_query_full(lot)
    )


def cian_land_search_url_cadastral_only(lot: Lot) -> str | None:
    return _marketplace_url_from_template(
        settings.cian_land_search_template, _marketplace_search_query_cadastral_only(lot)
    )
