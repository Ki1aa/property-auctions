"""MVP GIS ingest pipeline (tables mvp_gis_*)."""

from app.services.mvp.pipeline import run_mvp_ingest

__all__ = ["run_mvp_ingest"]
