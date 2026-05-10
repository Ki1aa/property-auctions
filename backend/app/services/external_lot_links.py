"""Deep links for lots: GIS Torgi, NSPD map, app SPA, Domclick search/map."""

from __future__ import annotations

from math import cos, radians
from urllib.parse import quote, urlencode

from app.config import settings
from app.models import Lot
from app.services.lot_identity import lot_notice_identity
from app.services.map_anchor import lot_map_display_coordinates
from app.services.nspd.geometry import epsg3857_to_4326, wgs84_to_epsg3857

TORGI_NOTICE_VIEW = "https://torgi.gov.ru/new/public/notices/view/{notice_number}"
# SPA route: opens the lot info tab (same as links from the notice page).
TORGI_LOT_VIEW = "https://torgi.gov.ru/new/public/lots/lot/{lot_code}/(lotInfo:info)"
NSPD_PUBLIC_MAP_URL = "https://nspd.gov.ru/map?thematic=PKK"
NSPD_MAP_BASE_PARAMS = {
    "thematic": "PKK",
    "theme_id": "1",
    "baseLayerId": "235",
    "is_copy_url": "true",
}


def _normalize_torgi_https(url: str | None) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    if u.startswith("http://torgi.gov.ru"):
        return "https://" + u[len("http://") :]
    return u
def _notice_reg_number(lot: Lot, notice_payload: dict | None) -> str | None:
    return lot_notice_identity(lot, notice_payload=notice_payload).reg_num


def _notice_lot_number(lot: Lot, lot_payload: dict | None) -> str | None:
    return lot_notice_identity(lot, latest_payload=lot_payload).lot_number


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
        href = _normalize_torgi_https(href) or href
        if href.startswith("https://torgi.gov.ru/new/public/notices/view/"):
            return href
        if href.startswith("/new/public/notices/view/"):
            return f"https://torgi.gov.ru{href}"
    return None


def torgi_notice_json_url(lot: Lot) -> str | None:
    """OpenData / notice detail JSON URL (href)."""
    return _normalize_torgi_https(lot.notice_detail_url or lot.source_url)


def torgi_notice_html_url(lot: Lot, notice_payload: dict | None = None) -> str | None:
    """Official SPA notice card on torgi.gov.ru when registry number is known."""
    official_href = _official_notice_href(notice_payload)
    if official_href:
        return official_href
    reg = _notice_reg_number(lot, notice_payload)
    if not reg:
        return None
    return TORGI_NOTICE_VIEW.format(notice_number=quote(reg, safe=""))


def torgi_lot_html_url(
    lot: Lot,
    lot_payload: dict | None = None,
    notice_payload: dict | None = None,
) -> str | None:
    """Official SPA lot card on torgi.gov.ru when notice and lot numbers are known."""
    identity = lot_notice_identity(lot, latest_payload=lot_payload, notice_payload=notice_payload)
    reg = identity.reg_num
    lot_number = identity.lot_number
    if not reg or not lot_number:
        return None
    lot_code = quote(f"{reg}_{lot_number}", safe="_")
    return TORGI_LOT_VIEW.format(lot_code=lot_code)


def torgi_public_url(
    lot: Lot,
    notice_payload: dict | None = None,
    lot_payload: dict | None = None,
) -> str | None:
    """Prefer human-readable lot page; fall back to notice page, then JSON."""
    return (
        torgi_lot_html_url(lot, lot_payload=lot_payload, notice_payload=notice_payload)
        or torgi_notice_html_url(lot, notice_payload)
        or torgi_notice_json_url(lot)
    )


def torgi_notice_json_link_when_distinct(
    lot: Lot,
    notice_payload: dict | None = None,
    lot_payload: dict | None = None,
) -> str | None:
    """Second link for UI/Telegram: raw JSON href when it differs from the HTML card URL."""
    html_urls = {
        (torgi_lot_html_url(lot, lot_payload=lot_payload, notice_payload=notice_payload) or "").strip().rstrip("/"),
        (torgi_notice_html_url(lot, notice_payload) or "").strip().rstrip("/"),
    }
    json_u = (torgi_notice_json_url(lot) or "").strip().rstrip("/")
    if not json_u:
        return None
    html_urls.discard("")
    if html_urls and json_u not in html_urls:
        return json_u.strip() or None
    return None


def nspd_map_url(
    cadastral_number: str | None,
    *,
    centroid_latitude: float | None = None,
    centroid_longitude: float | None = None,
    mercator_x: float | None = None,
    mercator_y: float | None = None,
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
    has_mercator = mercator_x is not None and mercator_y is not None
    has_wgs84 = centroid_latitude is not None and centroid_longitude is not None
    if has_mercator:
        params.update(
            {
                "zoom": "20",
                "coordinate_x": str(mercator_x),
                "coordinate_y": str(mercator_y),
            }
        )
    elif has_wgs84:
        x, y = wgs84_to_epsg3857(float(centroid_latitude), float(centroid_longitude))
        params.update(
            {
                "zoom": "20",
                "coordinate_x": str(x),
                "coordinate_y": str(y),
            }
        )
    if card_id_s and card_type_s and (has_mercator or has_wgs84):
        params["selectedCard"] = f"{card_id_s},{card_type_s},{cad}"
    else:
        params["query"] = cad
    return "https://nspd.gov.ru/map?" + urlencode(params, safe=":,")


def rosreestr_cadastral_map_url(cadastral_number: str | None) -> str | None:
    """Public cadastral map (ПКК): opens on nspd.gov.ru with cadastral query (Rosreestr PKK is hosted there)."""
    return nspd_map_url(cadastral_number)


def pkk_map_url(cadastral_number: str | None) -> str | None:
    """Same as :func:`rosreestr_cadastral_map_url` (legacy field name in API)."""
    return rosreestr_cadastral_map_url(cadastral_number)


def pkk_lot_map_url(lot: Lot) -> str | None:
    """PKK on NSPD: same deep link as :func:`nspd_lot_map_url` (zoom / selectedCard when enrichment exists)."""
    return nspd_lot_map_url(lot)


def nspd_lot_map_url(lot: Lot) -> str | None:
    coords = lot_map_display_coordinates(lot)
    lat, lon = coords if coords else (None, None)
    return nspd_map_url(
        lot.cadastral_number,
        centroid_latitude=lat,
        centroid_longitude=lon,
        mercator_x=lot.nspd_map_coordinate_x,
        mercator_y=lot.nspd_map_coordinate_y,
        card_id=lot.nspd_card_id,
        card_type=lot.nspd_card_type,
    )


def _domclick_map_center_wgs84(lot: Lot) -> tuple[float, float] | None:
    """Prefer stored NSPD Web Mercator center (same as map URL) for Domclick bbox."""
    mx = lot.nspd_map_coordinate_x
    my = lot.nspd_map_coordinate_y
    if mx is not None and my is not None:
        return epsg3857_to_4326(float(mx), float(my))
    return lot_map_display_coordinates(lot)


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


def _marketplace_url_from_template(
    template: str,
    query: str | None,
    *,
    enabled: bool | None = None,
) -> str | None:
    if enabled is None:
        enabled = settings.include_marketplace_search_urls
    if not enabled:
        return None
    q = (query or "").strip()
    if not q:
        return None
    t = (template or "").strip()
    if not t:
        return None
    enc = quote(q, safe="")
    return t.format(q=enc)


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


def _fmt_coord_bbox(value: float) -> str:
    """High-precision WGS84 for Domclick sw= / ne= (matches regional on-map links)."""
    s = f"{float(value):.14f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def domclick_land_map_url(lot: Lot) -> str | None:
    """On-map search around lot centroid: NSPD map Mercator center when stored, else map anchor / notice; bbox sw/ne."""
    if not settings.include_marketplace_map_urls:
        return None
    centroid = _domclick_map_center_wgs84(lot)
    if centroid is None:
        return None
    lat, lon = centroid
    south, west, north, east = _bbox_around_wgs84(lat, lon, settings.marketplace_map_radius_km)
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
    base = (settings.domclick_on_map_base_url or "").strip().rstrip("/")
    if not base:
        base = "https://domclick.ru/search/on-map"
    return f"{base}?" + urlencode(params, safe=",")


def domclick_land_search_url(lot: Lot) -> str | None:
    """Best-effort Domclick search; not a cadastral deep link."""
    return _marketplace_url_from_template(
        settings.domclick_search_template, _marketplace_search_query_full(lot)
    )


def domclick_land_search_url_cadastral_only(lot: Lot) -> str | None:
    if not settings.domclick_cadastral_search_enabled:
        return None
    return _marketplace_url_from_template(
        settings.domclick_search_template,
        _marketplace_search_query_cadastral_only(lot),
        enabled=True,
    )
