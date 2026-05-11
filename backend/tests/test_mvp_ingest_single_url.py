"""MVP ingest: optional single data-*.json URL bypasses discovery."""

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.services.mvp import pipeline as mvp_pipeline
from app.services.mvp.pipeline import run_mvp_ingest

# Register mvp_gis_* tables on Base
import app.models_mvp  # noqa: F401


def test_mvp_ingest_data_file_url_skips_discovery(monkeypatch):
    monkeypatch.setattr(settings, "ingest_land_filter_bidd_type_codes", "ZK", raising=False)
    monkeypatch.setattr(settings, "ingest_land_filter_relaxed", False, raising=False)
    monkeypatch.setattr(settings, "telegram_alerts_enabled", False, raising=False)

    discovery_called: list[bool] = []

    async def fake_build_discovery_plan(**kwargs):
        discovery_called.append(True)
        raise AssertionError("build_discovery_plan must not run when data_file_url is set")

    monkeypatch.setattr(mvp_pipeline, "build_discovery_plan", fake_build_discovery_plan)

    expected_url = (
        "https://torgi.gov.ru/new/opendata/7710568760-notice/"
        "data-20260509T0000-20260510T0000-structure-20240401.json"
    )
    fetched: list[str] = []

    async def fake_fetch(url: str):
        fetched.append(url)
        return {"data": []}, "testsha"

    monkeypatch.setattr(mvp_pipeline, "fetch_json_payload_with_meta", fake_fetch)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    try:
        stats = asyncio.run(
            run_mvp_ingest(db, dry_run=True, limit=10, data_file_url=expected_url),
        )
    finally:
        db.close()

    assert discovery_called == []
    assert fetched == [expected_url]
    assert stats.get("ingest_file_url") == expected_url
    assert stats.get("ingest_source_kind") == "cli_single"
    assert stats.get("records_fetched") == 0
    assert stats.get("upserted") == 0
    assert stats.get("would_upsert") == 0
