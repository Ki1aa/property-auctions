"""Defensive parser for ГИС Торги notice detail JSON.

The exact schema of notice detail documents is not formally published; the
opendata structure schema (`structure-20240401.json`) describes only the
*index* listObjects.  This parser walks the entire detail document tree and
extracts cadastral / land fields by:

- regex over the cadastral number canonical format `XX:XX:XXXXXXX:NN`,
- known field name aliases (recursive search),
- ИЖС keyword match across the whole serialized payload.

Field naming varies between rosreestr / torgi, so we keep multiple aliases
and prefer the first non-empty hit.  When a real detail sample becomes
available it should be added to tests for verification.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Iterable

# Cadastral number canonical format `XX:XX:XXXXXXX:NN`. We allow optional
# whitespace around colons because Torgi notice text occasionally inserts
# them (e.g. when copy-pasted from PDF). The matcher is greedy enough to
# handle non-standard last segments such as ":00".
CADASTRAL_RE = re.compile(r"\b\d{1,2}\s*:\s*\d{1,2}\s*:\s*\d{6,7}\s*:\s*\d+\b")

AREA_FIELD_ALIASES = (
    "estateArea",
    "objectArea",
    "area",
    "lotArea",
    "areaSqm",
    "squareValue",
    "amountObjectArea",
    "squarezu",
)
LAND_CATEGORY_ALIASES = (
    "landCategory",
    "estateLandCategory",
    "category",
    "categoryLand",
    "categoryName",
)
PERMITTED_USE_ALIASES = (
    "permittedUse",
    "permittedUses",
    "permittedUsage",
    "vri",
    "usageType",
    "usage",
    "estatePermittedUse",
)
ADDRESS_ALIASES = (
    "estateAddress",
    "address",
    "objectAddress",
    "fullAddress",
    "lotAddress",
    "estateLocation",
)
NAME_ALIASES = (
    "lotName",
    "noticeName",
    "name",
    "title",
    "subject",
    "estateName",
)
PRICE_ALIASES = (
    "startPrice",
    "initialPrice",
    "minPrice",
    "priceStart",
    "startBidPrice",
    "priceMin",
)

# Free-text fields searched for area / vri keywords as last resort.
DESCRIPTION_FIELD_ALIASES = (
    "lotDescription",
    "noticeDescription",
    "description",
    "lotName",
    "noticeName",
    "subject",
    "additionalInfo",
)

# Permitted use markers commonly found in lot/notice free text. Keys are
# lowercase substrings, values are canonical labels we emit when the parser
# falls back to text search.
PERMITTED_USE_TEXT_MARKERS: tuple[tuple[str, str], ...] = (
    ("индивидуальное жилищное строительство", "Для индивидуального жилищного строительства"),
    ("под ижс", "Для индивидуального жилищного строительства"),
    ("для ижс", "Для индивидуального жилищного строительства"),
    ("ижс", "Для индивидуального жилищного строительства"),
    ("личного подсобного хозяйства", "Для ведения личного подсобного хозяйства"),
    ("лпх", "Для ведения личного подсобного хозяйства"),
    ("крестьянско-фермерского хозяйства", "Для ведения крестьянского (фермерского) хозяйства"),
    ("крестьянского (фермерского) хозяйства", "Для ведения крестьянского (фермерского) хозяйства"),
    ("кфх", "Для ведения крестьянского (фермерского) хозяйства"),
    ("садоводств", "Для ведения садоводства"),
    ("огородничеств", "Для ведения огородничества"),
    ("дачного строительства", "Для дачного строительства"),
)

# Numeric area extractor with unit. Captures e.g. "1 500,75 кв.м", "0,12 га",
# "8 соток" and returns area in square metres after unit normalization.
AREA_UNIT_RE = re.compile(
    r"(?P<value>\d{1,3}(?:[ \u00a0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"\s*"
    r"(?P<unit>кв\.?\s*м|м\s*2|м²|га\b|гектар(?:ов|а)?|сот(?:\.|ок|ки|очек|очка|ой)?)",
    re.IGNORECASE,
)

UNIT_TO_SQM: dict[str, float] = {
    "кв.м": 1.0,
    "квм": 1.0,
    "м2": 1.0,
    "м²": 1.0,
    "га": 10000.0,
    "гектар": 10000.0,
    "сот": 100.0,
}


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).lower().strip()


def _walk(node: Any) -> Iterable[Any]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _find_first_string(payload: Any, aliases: tuple[str, ...]) -> str | None:
    aliases_lower = {alias.lower() for alias in aliases}
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            if key.lower() not in aliases_lower:
                continue
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                for nested in ("name", "value", "fullName", "displayName"):
                    nv = value.get(nested)
                    if isinstance(nv, str) and nv.strip():
                        return nv.strip()
            if isinstance(value, list):
                strings = [v for v in value if isinstance(v, str) and v.strip()]
                if strings:
                    return ", ".join(s.strip() for s in strings)
    return None


def _find_first_number(payload: Any, aliases: tuple[str, ...]) -> float | None:
    aliases_lower = {alias.lower() for alias in aliases}
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            if key.lower() not in aliases_lower:
                continue
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                cleaned = value.replace(",", ".").replace(" ", "").strip()
                try:
                    return float(cleaned)
                except ValueError:
                    continue
            if isinstance(value, dict):
                for nested in ("value", "amount", "sum"):
                    nv = value.get(nested)
                    if isinstance(nv, (int, float)):
                        return float(nv)
                    if isinstance(nv, str):
                        try:
                            return float(nv.replace(",", ".").replace(" ", ""))
                        except ValueError:
                            continue
    return None


def _find_cadastral_number(payload: Any) -> str | None:
    serialized = json.dumps(payload, ensure_ascii=False)
    match = CADASTRAL_RE.search(serialized)
    if not match:
        return None
    # Strip any whitespace introduced by tolerant regex.
    return re.sub(r"\s+", "", match.group(0))


def _characteristic_to_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("name", "value", "fullName", "displayName"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _characteristic_to_text(item)
            if text:
                parts.append(text)
        if parts:
            return ", ".join(parts)
    return None


def _find_characteristic_string(payload: Any, codes: tuple[str, ...]) -> str | None:
    code_set = {item.lower() for item in codes}
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        characteristics = node.get("characteristics")
        if not isinstance(characteristics, list):
            continue
        for characteristic in characteristics:
            if not isinstance(characteristic, dict):
                continue
            code = characteristic.get("code")
            if not isinstance(code, str) or code.lower() not in code_set:
                continue
            text = _characteristic_to_text(characteristic.get("characteristicValue"))
            if text:
                return text
    return None


def _find_characteristic_number(payload: Any, codes: tuple[str, ...]) -> float | None:
    text = _find_characteristic_string(payload, codes)
    if not text:
        return None
    cleaned = text.replace(",", ".").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_unit(unit_raw: str) -> str:
    unit = unit_raw.lower().replace(".", "").replace(" ", "").replace("\u00a0", "")
    if unit.startswith("м2") or unit == "м²" or unit == "квм":
        return "м2"
    if unit.startswith("га") or unit.startswith("гектар"):
        return "га"
    if unit.startswith("сот"):
        return "сот"
    return unit


def _parse_area_with_units(text: str) -> float | None:
    """Parse the first 'X unit' occurrence in free-form text.

    Returns area in square metres or None if no plausible match found.
    Skips clearly small/giant values (< 1 sqm or > 1e9 sqm) to avoid noise.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    for match in AREA_UNIT_RE.finditer(text):
        raw_value = match.group("value").replace("\u00a0", " ").replace(" ", "").replace(",", ".")
        try:
            value = float(raw_value)
        except ValueError:
            continue
        unit_canonical = _normalize_unit(match.group("unit"))
        if unit_canonical == "м2":
            sqm = value
        elif unit_canonical == "га":
            sqm = value * 10000.0
        elif unit_canonical == "сот":
            sqm = value * 100.0
        else:
            continue
        if 1.0 <= sqm <= 1e9:
            return sqm
    return None


def _find_area_in_text(payload: Any) -> float | None:
    for alias in DESCRIPTION_FIELD_ALIASES:
        text = _find_first_string(payload, (alias,))
        area = _parse_area_with_units(text or "")
        if area is not None:
            return area
    return None


def _find_permitted_use_in_text(payload: Any) -> str | None:
    for alias in DESCRIPTION_FIELD_ALIASES:
        text = _find_first_string(payload, (alias,))
        if not text:
            continue
        normalized = _normalize(text)
        for marker, canonical in PERMITTED_USE_TEXT_MARKERS:
            if marker in normalized:
                return canonical
    return None


def parse_notice_detail(payload: Any) -> dict[str, Any]:
    """Extract land-plot fields from a ГИС Торги notice detail JSON tree."""
    cadastral = _find_cadastral_number(payload)
    if cadastral is None:
        cadastral = _find_characteristic_string(
            payload,
            ("CadastralNumber", "cadastralNumber", "kadastrNumber", "estateCadastralNumber"),
        )
        if cadastral:
            cadastral = re.sub(r"\s+", "", cadastral)

    area_sqm = _find_first_number(payload, AREA_FIELD_ALIASES)
    if area_sqm is None:
        area_sqm = _find_characteristic_number(
            payload, ("SquareZU", "EstateArea", "LotSquare", "Square", "estateArea", "area", "lotArea")
        )
    if area_sqm is None:
        area_sqm = _find_area_in_text(payload)

    permitted_use = _find_first_string(payload, PERMITTED_USE_ALIASES)
    if permitted_use is None:
        permitted_use = _find_characteristic_string(
            payload, ("PermittedUse", "permittedUse", "vri", "EstatePermittedUse")
        )
    if permitted_use is None:
        permitted_use = _find_permitted_use_in_text(payload)

    return {
        "cadastral_number": cadastral,
        "area_sqm": area_sqm,
        "land_category": _find_first_string(payload, LAND_CATEGORY_ALIASES),
        "permitted_use": permitted_use,
        "address": _find_first_string(payload, ADDRESS_ALIASES),
        "lot_name": _find_first_string(payload, NAME_ALIASES),
        "start_price": _find_first_number(payload, PRICE_ALIASES),
    }


def match_izhs(payload: Any, keywords: list[str]) -> bool:
    """Return True when any IZHS keyword appears in any text of the payload."""
    if not keywords:
        return False
    haystack = _normalize(json.dumps(payload, ensure_ascii=False))
    return any(_normalize(keyword) in haystack for keyword in keywords if keyword.strip())


def split_keywords(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]
