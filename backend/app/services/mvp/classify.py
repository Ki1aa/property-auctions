"""Land / housing signal / blacklist classification for MVP ingest."""

from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.services.ingest.detail_parser import match_izhs, split_keywords
from app.services.mvp.land_filter_config import land_filter_codes

CADASTRE_RE = re.compile(
    r"\b\d{2}:\d{2}:\d{6,}:\d+\b|\b\d{2}:\d{2}:\d+:\d+\b",
    re.IGNORECASE,
)

HARD_BLACKLIST = (
    "транспортное средство",
    "автомобиль",
    "автомобил",
    "оборудование",
    "движимое имущество",
    "металлолом",
    "нежилое помещение",
    "жилое помещение",
    "квартира",
    "гараж",
    "машино-место",
)

BUILDING_MARKERS = ("здание", "сооружение")

LAND_HINT = ("земельный участ", "земельн", "участок под", "участок ")

HIGH_MARKERS = (
    "ижс",
    "индивидуальное жилищное строительство",
    "для индивидуального жилищного строительства",
    "жилой дом",
)

MEDIUM_MARKERS = (
    "лпх",
    "личное подсобное хозяйство",
    "ведение личного подсобного хозяйства",
    "садоводство",
    "садовый дом",
    "малоэтажная жилая застройка",
)


def _text_blob(normalized: dict[str, Any]) -> str:
    parts = [
        normalized.get("title"),
        normalized.get("land_category"),
        normalized.get("permitted_use"),
        normalized.get("address"),
        normalized.get("description"),
    ]
    raw = normalized.get("raw")
    if isinstance(raw, dict):
        parts.append(str(raw.get("noticeName") or ""))
        parts.append(str(raw.get("lotName") or ""))
    return " ".join(str(p).lower() for p in parts if p)


def _has_cadastre_in_text(text: str) -> bool:
    return CADASTRE_RE.search(text) is not None


def _has_land_hint(text: str) -> bool:
    return any(m in text for m in LAND_HINT)


def _soft_building_block(text: str) -> bool:
    """Do not treat building/sooruzhenie as blacklist if land plot or cadastre is present."""
    if _has_land_hint(text) or _has_cadastre_in_text(text):
        return True
    return False


def _hard_blacklist_hit(text: str) -> str | None:
    for m in HARD_BLACKLIST:
        if m in text:
            return m
    for m in BUILDING_MARKERS:
        if m in text and not _soft_building_block(text):
            return m
    return None


def _signal_from_text_and_izhs(normalized: dict[str, Any], text: str) -> str:
    scoped = normalized.get("raw")
    if match_izhs(scoped if isinstance(scoped, dict) else {}, split_keywords(settings.izhs_keywords)):
        return "HIGH"
    for m in HIGH_MARKERS:
        if m in text:
            return "HIGH"
    for m in MEDIUM_MARKERS:
        if m in text:
            return "MEDIUM"
    if _has_land_hint(text) or _has_cadastre_in_text(text):
        return "LOW"
    return "NONE"


def classify_normalized_lot(normalized: dict[str, Any]) -> dict[str, Any]:
    """Return is_land, is_housing_candidate, signal_level, is_ignored, ignored_reason."""
    text = _text_blob(normalized)
    codes = land_filter_codes()
    category = str(normalized.get("category") or "").strip()

    if settings.ingest_land_filter_relaxed or not codes:
        is_land = True
    else:
        is_land = bool(category) and category in codes

    ignored_reason = _hard_blacklist_hit(text)
    is_ignored = ignored_reason is not None

    if is_ignored:
        signal = "NONE"
        housing = False
    else:
        signal = _signal_from_text_and_izhs(normalized, text)
        if not is_land:
            signal = "NONE"
        housing = signal in ("HIGH", "MEDIUM")

    return {
        "is_land": is_land,
        "is_housing_candidate": housing,
        "signal_level": signal,
        "is_ignored": is_ignored,
        "ignored_reason": ignored_reason,
    }


def signal_rank(level: str) -> int:
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    return order.get((level or "NONE").upper(), 0)


def telegram_min_signal_rank() -> int:
    return signal_rank(settings.telegram_min_signal_level)


def lot_passes_telegram_signal(level: str) -> bool:
    return signal_rank(level) >= telegram_min_signal_rank()
