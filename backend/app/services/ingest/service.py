import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import IngestManifest, IngestRun, Lot, LotSnapshot, OpenDataNotice, Organizer
from app.services.alerts.service import notify_lot_event
from app.services.ingest.client import fetch_json_payload, fetch_json_payload_with_meta, save_raw_payload
from app.services.ingest.detail_parser import match_izhs, parse_notice_detail, split_keywords
from app.services.ingest.discovery import DiscoveredDatasetFile, build_discovery_plan
from app.services.ingest.normalizer import normalize_lot

logger = logging.getLogger(__name__)

DETAIL_FETCH_RETRY_BACKOFF_SEC = 1.5
STRUCTURE_VERSION_RE = re.compile(r"structure-(\d+)")
LOT_CREATING_OPENDATA_DOCUMENT_TYPES = frozenset(("notice",))
OPENDATA_EVENT_STATUS = {
    "noticeCancel": "CANCELED",
    "noticeStop": "STOPPED",
    "noticeResumption": "PUBLISHED",
    "noticeAnnulment": "ANNULLED",
}
SOURCE_UNAVAILABLE_MARKERS = (
    "torgi opendata:",
    "connecterror",
    "connecttimeout",
    "connection attempts failed",
    "connection timed out",
    "timed out",
    "server disconnected",
    "temporary failure",
)


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()


def _pick_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("listObjects", "data", "items", "results", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _is_torgi_opendata_error_envelope(payload: Any) -> bool:
    """Torgi returns HTTP 200 with {\"error\": \"...\"} when a slice is not published yet."""
    if not isinstance(payload, dict):
        return False
    err = payload.get("error")
    if not isinstance(err, str) or not err.strip():
        return False
    return len(_pick_items(payload)) == 0


def _classify_ingest_error(error: str) -> str:
    lowered = error.lower()
    if "unsupported structure version" in lowered:
        return "schema_migration_required"
    if any(marker in lowered for marker in SOURCE_UNAVAILABLE_MARKERS):
        return "source_unavailable"
    return "file_processing_error"


def _friendly_ingest_error(
    *, error: str, source_url: str | None = None, error_kind: str | None = None
) -> str:
    kind = error_kind or _classify_ingest_error(error)
    if kind == "source_unavailable":
        url_part = f" ({source_url})" if source_url else ""
        return (
            "Источник Torgi временно не отдает один из файлов (срез еще не опубликован или недоступен)."
            f"{url_part} Попробуйте повторить позже."
        )
    if kind == "schema_migration_required":
        return "Источник Torgi прислал файл с неподдерживаемой версией структуры. Нужна миграция парсера схемы."
    return error


def _supported_structure_versions() -> set[str]:
    values = [item.strip() for item in settings.supported_structure_versions.split(",")]
    return {item for item in values if item}


def _target_region_codes() -> set[str]:
    return {item.strip() for item in settings.target_region_codes.split(",") if item.strip()}


def _passes_region_filter(normalized: dict, allowed: set[str]) -> bool:
    if not allowed:
        return True
    region = normalized.get("region")
    return region is not None and str(region).strip() in allowed


def _is_manifest_processed(db: Session, source_url: str, sha256: str) -> bool:
    existing = db.scalar(
        select(IngestManifest.id).where(
            IngestManifest.source_url == source_url,
            IngestManifest.sha256 == sha256,
            IngestManifest.status == "processed",
        )
    )
    return existing is not None


def _last_processed_data_to(db: Session) -> datetime | None:
    return db.scalar(
        select(func.max(IngestManifest.data_to)).where(
            IngestManifest.provider == settings.ingest_provider,
            IngestManifest.dataset_id == settings.torgi_opendata_dataset_id,
            IngestManifest.status == "processed",
        )
    )


def _is_opendata_form(item: Any) -> bool:
    """Detect whether a raw item came from the opendata listObjects payload.

    Such items always carry both `regNum` and `href`. Other ingest sources
    (legacy /api/v1/auctions style) use different keys.
    """
    return (
        isinstance(item, dict)
        and isinstance(item.get("regNum"), str)
        and isinstance(item.get("href"), str)
    )


def _opendata_document_type(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    document_type = item.get("documentType")
    return document_type if isinstance(document_type, str) and document_type else None


def _creates_lot_from_opendata(item: Any) -> bool:
    document_type = _opendata_document_type(item)
    return document_type is None or document_type in LOT_CREATING_OPENDATA_DOCUMENT_TYPES


def _structure_version_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = STRUCTURE_VERSION_RE.search(url)
    return match.group(1) if match else None


def _parse_opendata_publish_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date_parser.parse(value)
    except (ValueError, TypeError):
        return None


def _upsert_opendata_notice(
    db: Session, item: dict[str, Any], structure_version: str | None
) -> OpenDataNotice | None:
    """Upsert OpenDataNotice for opendata-form items.

    Returns the persisted notice (with assigned id) or None if the item is
    not a recognizable opendata record.
    """
    if not _is_opendata_form(item):
        return None
    href = item["href"]
    publish_date = _parse_opendata_publish_date(item.get("publishDate"))

    existing = db.scalar(select(OpenDataNotice).where(OpenDataNotice.href == href))
    if existing is None:
        notice = OpenDataNotice(
            reg_num=item.get("regNum", ""),
            document_type=item.get("documentType"),
            publish_date=publish_date,
            href=href,
            bidder_org_code=item.get("bidderOrgCode"),
            right_holder_code=item.get("rightHolderCode"),
            bidd_type_code=item.get("biddTypeCode"),
            ownership_forms_code=item.get("ownershipFormsCode"),
            subject_estate_code=item.get("subjectEstateCode"),
            subject_right_holder_code=item.get("subjectRightHolderCode"),
            payload=item,
            structure_version=structure_version,
        )
        db.add(notice)
        db.flush()
        return notice

    existing.reg_num = item.get("regNum", existing.reg_num)
    existing.document_type = item.get("documentType")
    existing.publish_date = publish_date
    existing.bidder_org_code = item.get("bidderOrgCode")
    existing.right_holder_code = item.get("rightHolderCode")
    existing.bidd_type_code = item.get("biddTypeCode")
    existing.ownership_forms_code = item.get("ownershipFormsCode")
    existing.subject_estate_code = item.get("subjectEstateCode")
    existing.subject_right_holder_code = item.get("subjectRightHolderCode")
    existing.payload = item
    if structure_version:
        existing.structure_version = structure_version
    db.flush()
    return existing


def _apply_opendata_event_to_existing_lot(
    db: Session, item: dict[str, Any], *, opendata_notice_id: int | None
) -> bool:
    """Apply non-notice OpenData event documents without creating empty lots."""
    if not _is_opendata_form(item):
        return False
    document_type = _opendata_document_type(item)
    if document_type in LOT_CREATING_OPENDATA_DOCUMENT_TYPES:
        return False

    source_id = item.get("regNum")
    if not isinstance(source_id, str) or not source_id:
        return False

    lot = db.scalar(select(Lot).where(Lot.source_id == source_id))
    if lot is None:
        return False

    changed = False
    new_status = OPENDATA_EVENT_STATUS.get(document_type or "")
    if new_status and lot.status != new_status:
        lot.status = new_status
        changed = True
    if opendata_notice_id is not None and lot.opendata_notice_id is None:
        lot.opendata_notice_id = opendata_notice_id
        changed = True
    if changed:
        db.commit()
    return changed


def _write_manifest(
    db: Session,
    *,
    file_ref: DiscoveredDatasetFile,
    sha256: str,
    status: str,
    records_count: int,
    error_kind: str | None = None,
    error: str | None = None,
) -> None:
    manifest = IngestManifest(
        provider=settings.ingest_provider,
        dataset_id=settings.torgi_opendata_dataset_id,
        source_url=file_ref.source_url,
        structure_url=file_ref.structure_url,
        data_from=file_ref.data_from,
        data_to=file_ref.data_to,
        schema_version=file_ref.schema_version,
        sha256=sha256,
        processed_at=datetime.now(timezone.utc),
        status=status,
        records_count=records_count,
        error_kind=error_kind,
        error=error,
    )
    db.add(manifest)
    db.commit()


async def run_ingest(db: Session, mode: str | None = None) -> dict[str, int]:
    mode_value = (mode or settings.ingest_mode or "operational").lower()
    run = IngestRun(status="running", source_url=settings.ingest_source_url)
    db.add(run)
    db.commit()
    db.refresh(run)

    fetched_count = 0
    upserted_count = 0
    changed_count = 0
    processed_files = 0
    failed_files = 0
    last_failed_url: str | None = None
    last_error: str | None = None
    last_error_kind: str | None = None
    detail_fetch_count = 0
    allowed_regions = _target_region_codes()
    izhs_keywords = split_keywords(settings.izhs_keywords)

    try:
        last_processed_to = _last_processed_data_to(db) if mode_value == "operational" else None
        discovery_plan = await build_discovery_plan(mode=mode_value, last_processed_to=last_processed_to)
        source_url = discovery_plan.files[-1].source_url if discovery_plan.files else settings.ingest_source_url
        run.source_url = source_url
        db.commit()

        for file_ref in discovery_plan.files:
            try:
                payload, payload_sha = await fetch_json_payload_with_meta(file_ref.source_url)
                if _is_torgi_opendata_error_envelope(payload):
                    raise RuntimeError(f"Torgi opendata: {payload.get('error')}")
                if _is_manifest_processed(db, file_ref.source_url, payload_sha):
                    logger.info("Skipping already processed source URL: %s", file_ref.source_url)
                    continue

                if file_ref.structure_url:
                    await fetch_json_payload(file_ref.structure_url)

                supported_versions = _supported_structure_versions()
                if file_ref.schema_version and file_ref.schema_version not in supported_versions:
                    error_text = f"Unsupported structure version: {file_ref.schema_version}"
                    save_raw_payload(payload, run.id)
                    _write_manifest(
                        db,
                        file_ref=file_ref,
                        sha256=payload_sha,
                        status="schema_migration_required",
                        records_count=0,
                        error_kind="schema_migration_required",
                        error=error_text,
                    )
                    last_failed_url = file_ref.source_url
                    last_error = error_text
                    last_error_kind = "schema_migration_required"
                    failed_files += 1
                    continue

                save_raw_payload(payload, run.id)
                items = _pick_items(payload)
                fetched_count += len(items)

                structure_version = (
                    file_ref.schema_version
                    or _structure_version_from_url(file_ref.structure_url)
                )

                file_upserted = 0
                for item in items:
                    normalized = normalize_lot(item)
                    if not normalized["source_id"]:
                        continue
                    if not _passes_region_filter(normalized, allowed_regions):
                        continue

                    notice = _upsert_opendata_notice(db, item, structure_version)
                    notice_id = notice.id if notice is not None else None

                    if _is_opendata_form(item) and not _creates_lot_from_opendata(item):
                        if _apply_opendata_event_to_existing_lot(db, item, opendata_notice_id=notice_id):
                            changed_count += 1
                        continue

                    detail_fetch_count = await _maybe_enrich_with_detail(
                        normalized,
                        izhs_keywords=izhs_keywords,
                        already_fetched=detail_fetch_count,
                    )
                    if not _passes_region_filter(normalized, allowed_regions):
                        continue
                    is_changed = await _upsert_lot(db, normalized, opendata_notice_id=notice_id)
                    file_upserted += 1
                    upserted_count += 1
                    if is_changed:
                        changed_count += 1

                _write_manifest(
                    db,
                    file_ref=file_ref,
                    sha256=payload_sha,
                    status="processed",
                    records_count=file_upserted,
                )
                processed_files += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Ingest file failed: %s", file_ref.source_url)
                last_failed_url = file_ref.source_url
                last_error = str(exc)
                last_error_kind = _classify_ingest_error(last_error)
                _write_manifest(
                    db,
                    file_ref=file_ref,
                    sha256=_payload_hash({"source_url": file_ref.source_url, "run_id": run.id}),
                    status="failed",
                    records_count=0,
                    error_kind=last_error_kind,
                    error=str(exc),
                )
                failed_files += 1
                if mode_value != "backfill":
                    break

        if processed_files > 0 and failed_files == 0:
            run.status = "success"
        elif processed_files > 0:
            run.status = "partial_failed"
        elif failed_files > 0:
            run.status = "failed"
        else:
            run.status = "noop"
        run.fetched_count = fetched_count
        run.upserted_count = upserted_count
        run.changed_count = changed_count
        run.processed_files = processed_files
        run.failed_files = failed_files
        run.last_error_source_url = last_failed_url
        run.error_kind = last_error_kind
        run.finished_at = datetime.now(timezone.utc)
        if failed_files > 0:
            if last_error:
                friendly = _friendly_ingest_error(
                    error=last_error,
                    source_url=last_failed_url,
                    error_kind=last_error_kind,
                )
                run.error_message = f"{friendly} (processed={processed_files}, failed={failed_files})"
            else:
                run.error_message = f"processed={processed_files}, failed={failed_files}"
        elif run.status == "noop":
            run.error_message = "No new files to process (already ingested)."
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        run.status = "failed"
        last_error = str(exc)
        last_error_kind = _classify_ingest_error(last_error)
        run.processed_files = processed_files
        run.failed_files = failed_files
        run.last_error_source_url = last_failed_url
        run.error_kind = last_error_kind
        run.error_message = _friendly_ingest_error(
            error=last_error,
            source_url=last_failed_url,
            error_kind=last_error_kind,
        )
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return {
        "fetched_count": fetched_count,
        "upserted_count": upserted_count,
        "changed_count": changed_count,
        "processed_files": processed_files,
        "failed_files": failed_files,
    }


async def _fetch_detail_with_retry(detail_url: str) -> dict:
    """Fetch a single notice detail with one extra retry on transient failures.

    Torgi occasionally drops connections mid-response (`Server disconnected
    without sending a response`). One short retry is enough in practice and
    avoids hammering the source.
    """
    try:
        return await fetch_json_payload(detail_url)
    except Exception as first_exc:  # noqa: BLE001
        logger.info("Detail fetch transient error, retrying once: %s (%s)", detail_url, first_exc)
        await asyncio.sleep(DETAIL_FETCH_RETRY_BACKOFF_SEC)
        return await fetch_json_payload(detail_url)


async def _maybe_enrich_with_detail(
    normalized: dict,
    *,
    izhs_keywords: list[str],
    already_fetched: int,
) -> int:
    """Fetch notice detail JSON and merge cadastral fields into normalized.

    Returns updated counter of detail fetches (caller passes it back).
    """
    if not settings.ingest_fetch_notice_details:
        normalized.setdefault("is_izhs_candidate", False)
        return already_fetched
    if already_fetched >= settings.ingest_detail_max_per_run:
        normalized.setdefault("is_izhs_candidate", False)
        return already_fetched
    detail_url = normalized.get("source_url")
    if not detail_url:
        normalized.setdefault("is_izhs_candidate", False)
        return already_fetched

    try:
        detail = await _fetch_detail_with_retry(detail_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Detail fetch failed for %s: %s", detail_url, exc)
        normalized.setdefault("is_izhs_candidate", False)
        return already_fetched

    parsed = parse_notice_detail(detail)
    normalized["cadastral_number"] = parsed.get("cadastral_number")
    normalized["area_sqm"] = parsed.get("area_sqm")
    normalized["land_category"] = parsed.get("land_category")
    normalized["permitted_use"] = parsed.get("permitted_use")
    permitted_use_codes = parsed.get("permitted_use_codes")
    if isinstance(permitted_use_codes, list):
        normalized["permitted_use_codes"] = ", ".join(str(code) for code in permitted_use_codes if code)
    normalized["address"] = parsed.get("address")
    normalized["municipality"] = parsed.get("municipality")
    normalized["settlement"] = parsed.get("settlement")
    normalized["notice_detail_url"] = detail_url
    if parsed.get("subject_region_code"):
        normalized["region"] = parsed["subject_region_code"]
    if parsed.get("lot_name"):
        normalized["title"] = parsed["lot_name"]
    if parsed.get("start_price") is not None and not normalized.get("start_price"):
        normalized["start_price"] = parsed["start_price"]
    normalized["is_izhs_candidate"] = match_izhs(detail, izhs_keywords)
    return already_fetched + 1


async def _upsert_lot(
    db: Session, normalized: dict, *, opendata_notice_id: int | None = None
) -> bool:
    organizer_data = normalized["organizer"]
    organizer = db.scalar(select(Organizer).where(Organizer.source_id == organizer_data["source_id"]))
    if organizer is None:
        organizer = Organizer(**organizer_data)
        db.add(organizer)
        db.flush()
    else:
        organizer.name = organizer_data["name"]
        organizer.inn = organizer_data["inn"]
        organizer.kpp = organizer_data["kpp"]

    lot = db.scalar(select(Lot).where(Lot.source_id == normalized["source_id"]))
    created = False
    old_hash = None

    if lot is None:
        lot = Lot(source_id=normalized["source_id"], title=normalized["title"], organizer_id=organizer.id)
        db.add(lot)
        db.flush()
        created = True
    else:
        snapshot = db.scalar(
            select(LotSnapshot).where(LotSnapshot.lot_id == lot.id).order_by(LotSnapshot.id.desc())
        )
        old_hash = snapshot.payload_hash if snapshot else None

    lot.title = normalized["title"]
    lot.status = normalized["status"]
    lot.region = normalized["region"]
    lot.category = normalized["category"]
    lot.start_price = normalized["start_price"]
    lot.current_price = normalized["current_price"]
    lot.start_date = normalized["start_date"]
    lot.end_date = normalized["end_date"]
    lot.latitude = normalized["latitude"]
    lot.longitude = normalized["longitude"]
    lot.source_url = normalized["source_url"]
    lot.organizer_id = organizer.id
    lot.cadastral_number = normalized.get("cadastral_number")
    lot.area_sqm = normalized.get("area_sqm")
    lot.land_category = normalized.get("land_category")
    lot.permitted_use = normalized.get("permitted_use")
    lot.permitted_use_codes = normalized.get("permitted_use_codes")
    lot.address = normalized.get("address")
    lot.municipality = normalized.get("municipality")
    lot.settlement = normalized.get("settlement")
    lot.notice_detail_url = normalized.get("notice_detail_url")
    lot.is_izhs_candidate = bool(normalized.get("is_izhs_candidate"))
    if opendata_notice_id is not None:
        lot.opendata_notice_id = opendata_notice_id
    db.flush()

    new_hash = _payload_hash(normalized["raw"])
    changed = created or new_hash != old_hash
    if changed:
        db.add(LotSnapshot(lot_id=lot.id, payload_hash=new_hash, payload=normalized["raw"]))

    db.commit()

    if created:
        await notify_lot_event(db, lot, "new_lot", f"{lot.source_id}:{new_hash}")
    elif changed:
        await notify_lot_event(db, lot, "changed_lot", f"{lot.source_id}:{new_hash}")
    db.commit()
    return changed
