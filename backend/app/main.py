import logging
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update

from app.api import router as api_router
from app.database import Base, SessionLocal, engine
from app.models import IngestRun
from app.schemas import HealthResponse
from app.scheduler import scheduled_ingest, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="GIS Torgi Monitor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


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
                error_message="Interrupted before completion (stale ingest run).",
            )
        )
        if result.rowcount:
            logger.info("Closed %s stale ingest run(s)", result.rowcount)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    # Dev mode: create local schema automatically for SQLite workflow.
    Base.metadata.create_all(bind=engine)
    _close_stale_ingest_runs()
    start_scheduler()
    db = SessionLocal()
    try:
        has_runs = db.scalar(select(IngestRun.id).limit(1))
        if not has_runs:
            await scheduled_ingest()
    finally:
        db.close()


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")
