"""Deep links for lots: PKK, GIS Torgi (HTML + JSON), app SPA, marketplace search (best-effort)."""

from __future__ import annotations

import re
from urllib.parse import quote

from app.config import settings
from app.models import Lot

TORGI_NOTICE_VIEW = "https://torgi.gov.ru/new/public/notices/view/{notice_number}"


def _notice_reg_number(lot: Lot, notice_payload: dict | None) -> str | None:
    if notice_payload:
        for key in ("regNum", "noticeNumber", "reg_num"):
            raw = notice_payload.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
    sid = (lot.source_id or "").strip()
    if not sid or sid.lower().startswith("http"):
        return None
    # Registry numbers are typically long digit strings; avoid treating short garbage as regNum.
    if len(sid) < 8:
        return None
    if re.fullmatch(r"[\d\-:]+", sid):
        return sid
    if re.fullmatch(r"\d{10,}", sid):
        return sid
    return None


def torgi_notice_json_url(lot: Lot) -> str | None:
    """OpenData / notice detail JSON URL (href)."""
    return (lot.notice_detail_url or lot.source_url or "").strip() or None


def torgi_notice_html_url(lot: Lot, notice_payload: dict | None = None) -> str | None:
    """SPA notice card on torgi.gov.ru when registry number is known."""
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
    if not cadastral_number or not str(cadastral_number).strip():
        return None
    c = str(cadastral_number).strip()
    enc = quote(c, safe=":")
    return f"https://pkk.rosreestr.ru/#/search/{enc}/?text={enc}"


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
