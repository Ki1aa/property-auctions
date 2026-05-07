import logging
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.ingest.service import run_ingest

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_ingest_lock = asyncio.Lock()
_background_ingest_task: asyncio.Task[None] | None = None


async def _run_ingest_guarded(*, mode: str, trigger: str) -> None:
    if _ingest_lock.locked():
        logger.info("Skipping %s ingest: another ingest is already running", trigger)
        return
    db = SessionLocal()
    try:
        async with _ingest_lock:
            await run_ingest(db, mode=mode)
    except Exception:  # noqa: BLE001
        logger.exception("%s ingest failed", trigger.capitalize())
    finally:
        db.close()


async def scheduled_ingest() -> None:
    await _run_ingest_guarded(mode="operational", trigger="scheduled")


def is_ingest_running() -> bool:
    return _ingest_lock.locked() or (
        _background_ingest_task is not None and not _background_ingest_task.done()
    )


def start_manual_ingest(mode: str = "operational") -> bool:
    global _background_ingest_task
    if is_ingest_running():
        return False
    loop = asyncio.get_running_loop()
    _background_ingest_task = loop.create_task(_run_ingest_guarded(mode=mode, trigger="manual"))
    return True


def next_scheduled_ingest_at() -> datetime | None:
    job = scheduler.get_job("daily_ingest")
    return job.next_run_time if job is not None else None


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(scheduled_ingest, "interval", minutes=settings.ingest_interval_minutes, id="daily_ingest")
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
