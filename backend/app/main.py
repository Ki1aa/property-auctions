import logging

from fastapi import FastAPI
from sqlalchemy import select

from app.api import router as api_router
from app.database import Base, SessionLocal, engine
from app.models import IngestRun
from app.schemas import HealthResponse
from app.scheduler import scheduled_ingest, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="GIS Torgi Monitor")
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    # Dev mode: create local schema automatically for SQLite workflow.
    Base.metadata.create_all(bind=engine)
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
