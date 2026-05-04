import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.ingest.service import run_ingest

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_ingest() -> None:
    db = SessionLocal()
    try:
        await run_ingest(db, mode="operational")
    except Exception:  # noqa: BLE001
        logger.exception("Scheduled ingest failed")
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(scheduled_ingest, "interval", minutes=settings.ingest_interval_minutes, id="daily_ingest")
    scheduler.start()
