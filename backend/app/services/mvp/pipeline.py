"""MVP GIS ingest: OpenData -> mvp_gis_notices / mvp_gis_lots (+ versions, optional Telegram)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models_mvp import MvpGisLot, MvpGisLotVersion, MvpGisNotice
from app.services.ingest.client import fetch_json_payload_with_meta
from app.services.ingest.detail_parser import split_keywords
from app.services.ingest.discovery import build_discovery_plan
from app.services.ingest.normalizer import normalize_lot
from app.services.ingest.service import (
    _is_opendata_form,
    _is_torgi_opendata_error_envelope,
    _last_processed_data_to,
    _maybe_enrich_with_detail,
    _pick_items,
    _supported_structure_versions,
)
from app.services.mvp.classify import classify_normalized_lot, lot_passes_telegram_signal
from app.services.mvp.content_hash import (
    BUSINESS_HASH_FIELDS,
    business_state_from_normalized,
    compute_content_hash,
    diff_business_fields,
)
from app.services.mvp.land_filter_config import validate_land_filter_for_ingest
from app.services.mvp.link_builder import (
    build_domclick_map_url,
    build_lot_url,
    build_notice_url,
    build_nspd_search_url,
    resolve_notice_href_from_raw,
)
from app.services.mvp import mvp_telegram

logger = logging.getLogger(__name__)


def _attach_description(normalized: dict[str, Any]) -> None:
    raw = normalized.get("raw")
    if not isinstance(raw, dict):
        return
    lot_payload = raw.get("_notice_lot")
    if isinstance(lot_payload, dict):
        desc = lot_payload.get("lotDescription") or lot_payload.get("description")
        if desc and not normalized.get("description"):
            normalized["description"] = str(desc).strip()


def _notice_number_from(normalized: dict[str, Any]) -> str:
    return str(normalized.get("notice_reg_num") or normalized.get("source_id") or "").strip()


def _lot_number_from(normalized: dict[str, Any]) -> str:
    return str(normalized.get("notice_lot_number") or "1").strip()


def _lot_external_id_from(normalized: dict[str, Any], notice_number: str, lot_number: str) -> str:
    sid = str(normalized.get("source_id") or "").strip()
    if sid:
        return sid
    return f"{notice_number}_{lot_number}"


def _ensure_notice(
    db: Session,
    *,
    notice_number: str,
    title: str | None,
    status: str | None,
    publication_date: datetime | None,
    source_url: str | None,
    raw_data: dict[str, Any] | None,
) -> MvpGisNotice:
    row = db.scalar(select(MvpGisNotice).where(MvpGisNotice.notice_number == notice_number))
    now = datetime.now(timezone.utc)
    if row is None:
        row = MvpGisNotice(
            notice_number=notice_number,
            title=title,
            status=status,
            publication_date=publication_date,
            source_url=source_url,
            raw_data=raw_data,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(row)
        db.flush()
        return row
    row.title = title or row.title
    row.status = status or row.status
    row.publication_date = publication_date or row.publication_date
    row.source_url = source_url or row.source_url
    if raw_data is not None:
        row.raw_data = raw_data
    row.last_seen_at = now
    db.flush()
    return row


def _urls_for_lot(notice_number: str, lot_number: str, cadastral: str | None, lat: float | None, lon: float | None, raw: dict | None):
    notice_href = resolve_notice_href_from_raw(raw if isinstance(raw, dict) else None)
    notice_url = notice_href or build_notice_url(notice_number)
    lot_url = build_lot_url(notice_number, lot_number)
    nspd_url = build_nspd_search_url(cadastral or "") or None
    domclick_url = build_domclick_map_url(lat, lon)
    return notice_url, lot_url, nspd_url or None, domclick_url


async def run_mvp_ingest(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    validate_land_filter_for_ingest(dry_run=dry_run)

    stats: dict[str, Any] = {
        "records_fetched": 0,
        "land_rows": 0,
        "signal_high": 0,
        "signal_medium": 0,
        "signal_low": 0,
        "signal_none": 0,
        "ignored": 0,
        "region_72": 0,
        "would_telegram": [],
        "filtered_telegram": [],
        "upserted": 0,
    }

    mode_value = (settings.ingest_mode or "operational").lower()
    last_processed_to = _last_processed_data_to(db) if mode_value == "operational" else None
    discovery_plan = await build_discovery_plan(mode=mode_value, last_processed_to=last_processed_to)
    if not discovery_plan.files:
        stats["error"] = "No discovery files"
        return stats

    file_ref = discovery_plan.files[-1]
    payload, _payload_sha = await fetch_json_payload_with_meta(file_ref.source_url)
    if _is_torgi_opendata_error_envelope(payload):
        stats["error"] = str(payload.get("error"))
        return stats

    supported_versions = _supported_structure_versions()
    if file_ref.schema_version and file_ref.schema_version not in supported_versions:
        stats["error"] = f"Unsupported structure version: {file_ref.schema_version}"
        return stats

    items = _pick_items(payload)
    izhs_keywords = split_keywords(settings.izhs_keywords)
    detail_fetch_count = 0

    processed = 0
    for item in items:
        if limit is not None and processed >= limit:
            break
        if not _is_opendata_form(item):
            continue
        normalized = normalize_lot(item)
        if not normalized.get("source_id"):
            continue
        stats["records_fetched"] += 1
        processed += 1

        detail_fetch_count, normalized_lots = await _maybe_enrich_with_detail(
            normalized,
            izhs_keywords=izhs_keywords,
            already_fetched=detail_fetch_count,
        )

        for lot_norm in normalized_lots:
            _attach_description(lot_norm)
            notice_number = _notice_number_from(lot_norm)
            if not notice_number:
                continue
            lot_number = _lot_number_from(lot_norm)
            lot_external_id = _lot_external_id_from(lot_norm, notice_number, lot_number)
            cl = classify_normalized_lot(lot_norm)
            sig = cl["signal_level"]
            if sig == "HIGH":
                stats["signal_high"] += 1
            elif sig == "MEDIUM":
                stats["signal_medium"] += 1
            elif sig == "LOW":
                stats["signal_low"] += 1
            else:
                stats["signal_none"] += 1
            if cl["is_ignored"]:
                stats["ignored"] += 1

            if not cl["is_land"] or cl["is_ignored"]:
                continue
            stats["land_rows"] += 1

            region_code = str(lot_norm.get("region") or "").strip() or None
            if region_code == "72":
                stats["region_72"] += 1

            would_send = (
                region_code == "72"
                and lot_passes_telegram_signal(cl["signal_level"])
                and not cl["is_ignored"]
            )
            if would_send:
                stats["would_telegram"].append(f"{lot_external_id} ({cl['signal_level']})")
            else:
                reason_parts = []
                if region_code != "72":
                    reason_parts.append(f"region={region_code!r}")
                if not lot_passes_telegram_signal(cl["signal_level"]):
                    reason_parts.append(
                        f"signal={cl['signal_level']}<min={settings.telegram_min_signal_level}"
                    )
                stats["filtered_telegram"].append(f"{lot_external_id}: " + ", ".join(reason_parts))

            new_hash = compute_content_hash(lot_norm)
            lat = lot_norm.get("latitude")
            lon = lot_norm.get("longitude")
            if lat is not None:
                lat = float(lat)
            if lon is not None:
                lon = float(lon)
            notice_url, lot_url, nspd_url, domclick_url = _urls_for_lot(
                notice_number,
                lot_number,
                lot_norm.get("cadastral_number"),
                lat,
                lon,
                lot_norm.get("raw") if isinstance(lot_norm.get("raw"), dict) else None,
            )

            if dry_run:
                stats["upserted"] += 1
                continue

            notice = _ensure_notice(
                db,
                notice_number=notice_number,
                title=str((item.get("noticeName") or lot_norm.get("title") or "")[:1024] or None),
                status=str(lot_norm.get("status") or item.get("documentType") or "")[:128] or None,
                publication_date=lot_norm.get("start_date"),
                source_url=str(item.get("href") or "")[:2048] or None,
                raw_data=item if isinstance(item, dict) else None,
            )

            existing = db.scalar(select(MvpGisLot).where(MvpGisLot.lot_external_id == lot_external_id))
            before_state = (
                business_state_from_normalized({k: getattr(existing, k, None) for k in BUSINESS_HASH_FIELDS})
                if existing
                else {}
            )

            now = datetime.now(timezone.utc)
            start_price = lot_norm.get("start_price")
            if start_price is not None:
                start_price = float(start_price)
            area_sqm = lot_norm.get("area_sqm")
            if area_sqm is not None:
                area_sqm = float(area_sqm)
            price_per_sqm = None
            price_per_100sqm = None
            if start_price is not None and area_sqm is not None and area_sqm > 0:
                price_per_sqm = start_price / area_sqm
                price_per_100sqm = start_price / (area_sqm / 100.0)

            fields = {
                "notice_id": notice.id,
                "notice_number": notice_number,
                "lot_number": lot_number,
                "lot_external_id": lot_external_id,
                "region_code": region_code,
                "category": (str(lot_norm.get("category") or "")[:128] or None),
                "title": (str(lot_norm.get("title") or "")[:1024] or None),
                "description": (str(lot_norm.get("description") or "")[:8000] or None),
                "cadastral_number": (str(lot_norm.get("cadastral_number") or "")[:64] or None),
                "address": (str(lot_norm.get("address") or "")[:8000] or None),
                "area_sqm": area_sqm,
                "start_price": start_price,
                "status": (str(lot_norm.get("status") or "")[:128] or None),
                "application_start": lot_norm.get("application_start"),
                "application_end": lot_norm.get("application_end"),
                "auction_date": lot_norm.get("end_date"),
                "permitted_use": (str(lot_norm.get("permitted_use") or "")[:8000] or None),
                "land_category": (str(lot_norm.get("land_category") or "")[:512] or None),
                "price_per_sqm": price_per_sqm,
                "price_per_100sqm": price_per_100sqm,
                "lat": lat,
                "lon": lon,
                "coordinates_source": "notice" if lat and lon else None,
                "coordinates_updated_at": now if lat and lon else None,
                "notice_url": notice_url,
                "lot_url": lot_url,
                "nspd_url": nspd_url,
                "domclick_url": domclick_url,
                "content_hash": new_hash,
                "raw_data": lot_norm.get("raw") if isinstance(lot_norm.get("raw"), dict) else None,
                "is_land": cl["is_land"],
                "is_housing_candidate": cl["is_housing_candidate"],
                "signal_level": cl["signal_level"],
                "is_ignored": cl["is_ignored"],
                "ignored_reason": cl["ignored_reason"],
                "last_seen_at": now,
            }

            if existing is None:
                row = MvpGisLot(
                    **fields,
                    first_seen_at=now,
                )
                db.add(row)
                db.flush()
                after_st = business_state_from_normalized(lot_norm)
                diff = {k: {"old": None, "new": after_st.get(k)} for k in BUSINESS_HASH_FIELDS}
                db.add(
                    MvpGisLotVersion(
                        lot_id=row.id,
                        content_hash=new_hash,
                        changed_fields_json=diff,
                        raw_data=lot_norm.get("raw") if isinstance(lot_norm.get("raw"), dict) else None,
                    )
                )
                await mvp_telegram.notify_mvp_lot_if_needed(db, row, event_type="new_lot", content_hash=new_hash)
                stats["upserted"] += 1
                continue

            old_hash = existing.content_hash
            for key, value in fields.items():
                setattr(existing, key, value)
            db.flush()

            if old_hash != new_hash:
                diff = diff_business_fields(before_state, business_state_from_normalized(lot_norm))
                db.add(
                    MvpGisLotVersion(
                        lot_id=existing.id,
                        content_hash=new_hash,
                        changed_fields_json=diff,
                        raw_data=lot_norm.get("raw") if isinstance(lot_norm.get("raw"), dict) else None,
                    )
                )
                await mvp_telegram.notify_mvp_lot_if_needed(
                    db, existing, event_type="changed_lot", content_hash=new_hash
                )
            stats["upserted"] += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return stats