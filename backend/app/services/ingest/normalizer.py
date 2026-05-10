from datetime import datetime
from typing import Any

from dateutil import parser as date_parser


def _pick(data: dict[str, Any], *keys: str):
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError):
        return None


def _opendata_notice_row_title(item: dict[str, Any], reg_num: str) -> str:
    """Lot-scoped title for OpenData index rows; avoid notice-level noticeName in Lot.title."""
    lots = item.get("lots")
    if isinstance(lots, list):
        for row in lots:
            if not isinstance(row, dict):
                continue
            fragment = _pick(row, "lotName", "name", "title", "subject", "lotDescription")
            if fragment not in (None, ""):
                return str(fragment).strip()
    if reg_num:
        return f"Лот 1 · {reg_num}"
    return "Лот"


def normalize_lot(item: dict[str, Any]) -> dict[str, Any]:
    # OpenData notice dataset fallback fields
    if "regNum" in item and "href" in item:
        reg_num = str(_pick(item, "regNum") or "")
        title = _opendata_notice_row_title(item, reg_num)
        right_holder = str(_pick(item, "rightHolderCode") or "")
        bidder = str(_pick(item, "bidderOrgCode") or "")
        organizer_code = right_holder or bidder or "unknown"

        return {
            "source_id": reg_num or str(_pick(item, "href") or ""),
            "title": title,
            "status": _pick(item, "documentType"),
            "region": _pick(item, "subjectEstateCode"),
            "category": _pick(item, "biddTypeCode", "subjectEstateCode"),
            "start_price": None,
            "current_price": None,
            "start_date": parse_dt(_pick(item, "publishDate")),
            "end_date": None,
            "latitude": None,
            "longitude": None,
            "source_url": _pick(item, "href"),
            "organizer": {
                "source_id": organizer_code,
                "name": str(_pick(item, "rightHolderCode", "bidderOrgCode") or "Не указан"),
                "inn": None,
                "kpp": None,
            },
            "raw": item,
        }

    organizer = _pick(item, "organizer", "owner", "seller") or {}
    location = _pick(item, "location", "address") or {}

    lat = _pick(location, "lat", "latitude", "y")
    lon = _pick(location, "lon", "lng", "longitude", "x")

    return {
        "source_id": str(_pick(item, "id", "noticeNumber", "lotId", "code") or ""),
        "title": str(_pick(item, "name", "title", "subject") or "Без названия"),
        "status": _pick(item, "status", "state"),
        "region": _pick(item, "region", "regionName"),
        "category": _pick(item, "category", "lotType", "propertyType"),
        "start_price": _pick(item, "startPrice", "initialPrice"),
        "current_price": _pick(item, "currentPrice", "price"),
        "start_date": parse_dt(_pick(item, "startDate", "publishDate")),
        "end_date": parse_dt(_pick(item, "endDate", "biddingDate")),
        "latitude": float(lat) if lat is not None else None,
        "longitude": float(lon) if lon is not None else None,
        "source_url": _pick(item, "url", "sourceUrl"),
        "organizer": {
            "source_id": str(_pick(organizer, "id", "code", "inn") or "unknown"),
            "name": str(_pick(organizer, "name", "fullName") or "Не указан"),
            "inn": _pick(organizer, "inn"),
            "kpp": _pick(organizer, "kpp"),
        },
        "raw": item,
    }
