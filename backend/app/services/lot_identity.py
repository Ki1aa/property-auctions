"""Stable identity helpers for GIS Torgi multi-lot notices."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LotNoticeIdentity:
    reg_num: str | None = None
    lot_number: str | None = None
    lot_count: int | None = None


def _clean_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _positive_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    raw = str(value).strip()
    if not raw.isdigit():
        return None
    parsed = int(raw)
    return parsed if parsed > 0 else None


def _reg_num_from_payload(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    for key in ("regNum", "noticeNumber", "reg_num"):
        found = _clean_str(payload.get(key))
        if found:
            return found
    common_info = payload.get("commonInfo")
    if isinstance(common_info, dict):
        found = _clean_str(common_info.get("noticeNumber"))
        if found:
            return found
    export_object = payload.get("exportObject")
    if isinstance(export_object, dict):
        structured = export_object.get("structuredObject")
        if isinstance(structured, dict):
            notice = structured.get("notice")
            if isinstance(notice, dict):
                common_info = notice.get("commonInfo")
                if isinstance(common_info, dict):
                    found = _clean_str(common_info.get("noticeNumber"))
                    if found:
                        return found
    return None


def _identity_from_source_id(source_id: str | None) -> tuple[str | None, str | None]:
    sid = _clean_str(source_id)
    if not sid or sid.lower().startswith("http"):
        return None, None
    if len(sid) >= 10 and re.fullmatch(r"\d+", sid):
        return sid, "1"
    multi_lot_match = re.fullmatch(r"(\d{10,}):lot:(.+)", sid)
    if multi_lot_match:
        return multi_lot_match.group(1), _clean_str(multi_lot_match.group(2))
    return None, None


def _identity_from_lot_payload(payload: dict[str, Any] | None) -> tuple[str | None, int | None]:
    if not payload:
        return None, None

    lot_count = _positive_int(payload.get("_notice_lot_count"))
    raw_lot = payload.get("_notice_lot")
    if isinstance(raw_lot, dict):
        lot_number = _clean_str(raw_lot.get("lotNumber"))
        if lot_number:
            return lot_number, lot_count

    lot_number = _clean_str(payload.get("lotNumber"))
    if lot_number:
        return lot_number, lot_count

    raw_index = payload.get("_notice_lot_index")
    if isinstance(raw_index, int) and raw_index >= 0:
        return str(raw_index + 1), lot_count

    return None, lot_count


def notice_identity_from_values(
    *,
    source_id: str | None = None,
    notice_reg_num: str | None = None,
    notice_lot_number: str | None = None,
    notice_lot_count: int | None = None,
    latest_payload: dict[str, Any] | None = None,
    notice_payload: dict[str, Any] | None = None,
) -> LotNoticeIdentity:
    source_reg_num, source_lot_number = _identity_from_source_id(source_id)
    payload_lot_number, payload_lot_count = _identity_from_lot_payload(latest_payload)

    reg_num = _clean_str(notice_reg_num) or _reg_num_from_payload(notice_payload) or source_reg_num
    lot_number = _clean_str(notice_lot_number) or payload_lot_number or source_lot_number
    lot_count = _positive_int(notice_lot_count) or payload_lot_count

    if lot_count and lot_count > 1 and lot_number is None:
        lot_number = "1"

    return LotNoticeIdentity(reg_num=reg_num, lot_number=lot_number, lot_count=lot_count)


def lot_notice_identity(
    lot: Any,
    latest_payload: dict[str, Any] | None = None,
    notice_payload: dict[str, Any] | None = None,
) -> LotNoticeIdentity:
    return notice_identity_from_values(
        source_id=getattr(lot, "source_id", None),
        notice_reg_num=getattr(lot, "notice_reg_num", None),
        notice_lot_number=getattr(lot, "notice_lot_number", None),
        notice_lot_count=getattr(lot, "notice_lot_count", None),
        latest_payload=latest_payload,
        notice_payload=notice_payload,
    )


def lot_preferred_list_title(
    lot: Any,
    latest_payload: dict[str, Any] | None = None,
    notice_payload: dict[str, Any] | None = None,
) -> str:
    """Display title for a trading lot (not the notice name): snapshot lotName, cadastre, Лот N · regNum, then DB title."""
    if isinstance(latest_payload, dict):
        sub = latest_payload.get("_notice_lot")
        if isinstance(sub, dict):
            for key in ("lotName", "lotDescription"):
                fragment = str(sub.get(key) or "").strip()
                if fragment:
                    return fragment

    ident = lot_notice_identity(lot, latest_payload=latest_payload, notice_payload=notice_payload)
    lot_n = ident.lot_number
    lot_c = ident.lot_count
    multi = lot_c is not None and lot_c > 1
    cad = _clean_str(getattr(lot, "cadastral_number", None))
    reg = _clean_str(ident.reg_num)

    if multi and lot_n:
        if cad:
            return f"Лот {lot_n}: {cad}"
        if reg:
            return f"Лот {lot_n} · {reg}"
        return f"Лот {lot_n}"

    if cad:
        return cad

    if lot_n:
        if reg:
            return f"Лот {lot_n} · {reg}"
        return f"Лот {lot_n}"

    return _clean_str(getattr(lot, "title", None)) or "Без названия"
