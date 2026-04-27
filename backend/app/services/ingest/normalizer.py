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


def normalize_lot(item: dict[str, Any]) -> dict[str, Any]:
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
