import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update

from app.api import router as api_router
from app.mvp_api import router as mvp_api_router
from app.config import settings
from app.database import Base, SessionLocal, engine
from app import models_mvp  # noqa: F401  — register MVP GIS tables on Base.metadata
from app.models import IngestRun
from app.schemas import HealthResponse
from app.scheduler import scheduled_ingest, start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _is_sqlite_url(url: str) -> bool:
    lowered = (url or "").strip().lower()
    return lowered.startswith("sqlite") or "+sqlite" in lowered

def _close_stale_ingest_runs() -> None:
    """Mark long-running ingest rows as failed after unclean shutdown."""
    threshold = datetime.now(timezone.utc) - timedelta(hours=6)
    db = SessionLocal()
    try:
        result = db.execute(
            update(IngestRun)
            .where(IngestRun.status == "running", IngestRun.started_at < threshold)
            .values(
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error_kind="interrupted",
                error_message="Interrupted before completion (stale ingest run).",
            )
        )
        if result.rowcount:
            logger.info("Closed %s stale ingest run(s)", result.rowcount)
        db.commit()
    finally:
        db.close()


async def _startup() -> None:
    # SQLite dev: create missing tables. PostgreSQL/production: use Alembic migrations.
    if _is_sqlite_url(settings.database_url):
        Base.metadata.create_all(bind=engine)
    _close_stale_ingest_runs()
    start_scheduler()
    db = SessionLocal()
    try:
        has_runs = db.scalar(select(IngestRun.id).limit(1))
        if settings.run_ingest_on_startup and not has_runs:
            await scheduled_ingest()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _startup()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="GIS Torgi Monitor", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(mvp_api_router)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
