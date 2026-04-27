import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import IngestRun, Lot, LotSnapshot, Organizer
from app.services.alerts.service import notify_lot_event
from app.services.ingest.client import fetch_json_payload, save_raw_payload
from app.services.ingest.normalizer import normalize_lot

logger = logging.getLogger(__name__)


def _payload_hash(payload: dict) -> str:
    return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()


def _pick_items(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


async def run_ingest(db: Session) -> dict[str, int]:
    run = IngestRun(status="running", source_url=settings.ingest_source_url)
    db.add(run)
    db.commit()
    db.refresh(run)

    fetched_count = 0
    upserted_count = 0
    changed_count = 0

    try:
        payload = await fetch_json_payload(settings.ingest_source_url)
        save_raw_payload(payload, run.id)
        items = _pick_items(payload)
        fetched_count = len(items)

        for item in items:
            normalized = normalize_lot(item)
            if not normalized["source_id"]:
                continue
            is_changed = await _upsert_lot(db, normalized)
            upserted_count += 1
            if is_changed:
                changed_count += 1

        run.status = "success"
        run.fetched_count = fetched_count
        run.upserted_count = upserted_count
        run.changed_count = changed_count
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return {
        "fetched_count": fetched_count,
        "upserted_count": upserted_count,
        "changed_count": changed_count,
    }


async def _upsert_lot(db: Session, normalized: dict) -> bool:
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
