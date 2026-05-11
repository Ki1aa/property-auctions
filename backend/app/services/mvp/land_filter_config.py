"""Land-filter config validation for MVP ingest."""

from __future__ import annotations

from app.config import settings


def land_filter_codes() -> set[str]:
    raw = (settings.ingest_land_filter_bidd_type_codes or "").strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def validate_land_filter_for_ingest(*, dry_run: bool = False) -> None:
    """Refuse production ingest when land-filter config is empty unless relaxed (dev/debug)."""
    codes = land_filter_codes()
    if codes:
        return
    if settings.ingest_land_filter_relaxed:
        return
    if dry_run:
        return
    raise RuntimeError(
        "INGEST_LAND_FILTER_BIDD_TYPE_CODES is empty. Set comma-separated biddTypeCode values "
        "(e.g. ZK) after field research, or set INGEST_LAND_FILTER_RELAXED=true for dev/debug only."
    )
