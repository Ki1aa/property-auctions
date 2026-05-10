"""Apply NSPD geoportal Feature data to Lot ORM fields."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Lot
from app.services.nspd.client import NspdGeoportalClient
from app.services.nspd.geometry import polygon_centroid_lat_lon

logger = logging.getLogger(__name__)


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_text(*values: Any) -> str | None:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def extract_nspd_options_from_feature(feature: dict[str, Any]) -> dict[str, Any]:
    props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
    opts = props.get("options") if isinstance(props.get("options"), dict) else {}
    area = _parse_float(opts.get("specified_area"))
    cost = _parse_float(opts.get("cost_value"))
    addr = opts.get("readable_address")
    addr_s = str(addr).strip() if addr is not None and str(addr).strip() else None
    geom = feature.get("geometry") if isinstance(feature.get("geometry"), dict) else None
    centroid = polygon_centroid_lat_lon(geom) if geom else None
    lat, lon = centroid if centroid else (None, None)
    card_id = _first_text(
        feature.get("id"),
        props.get("id"),
        props.get("objectId"),
        props.get("object_id"),
        props.get("featureId"),
        opts.get("id"),
        opts.get("objectId"),
        opts.get("object_id"),
        opts.get("featureId"),
    )
    card_type = _first_text(
        props.get("category"),
        props.get("type"),
        props.get("layer_id"),
        props.get("layerId"),
        props.get("object_type"),
        opts.get("category"),
        opts.get("type"),
        opts.get("layer_id"),
        opts.get("layerId"),
        opts.get("object_type"),
    )
    return {
        "nspd_specified_area_sqm": area,
        "nspd_cost_value": cost,
        "nspd_readable_address": addr_s,
        "nspd_centroid_latitude": lat,
        "nspd_centroid_longitude": lon,
        "nspd_card_id": card_id,
        "nspd_card_type": card_type,
    }


def merge_nspd_into_notice_fields(lot: Lot, nspd_area: float | None, nspd_addr: str | None) -> None:
    """Copy NSPD options into Lot.area_sqm / Lot.address per settings (primary remains notice by default)."""
    ap = settings.nspd_merge_area_policy
    if nspd_area is not None and ap != "notice_only":
        if ap == "prefer_nspd":
            lot.area_sqm = nspd_area
        elif ap == "nspd_when_notice_missing" and (lot.area_sqm is None or lot.area_sqm <= 0):
            lot.area_sqm = nspd_area

    addr_p = settings.nspd_merge_address_policy
    if nspd_addr and addr_p != "notice_only":
        if addr_p == "prefer_nspd":
            lot.address = nspd_addr
        elif addr_p == "nspd_when_notice_missing" and not (lot.address or "").strip():
            lot.address = nspd_addr


def apply_nspd_features_to_lot(lot: Lot, features: list[dict[str, Any]]) -> None:
    """Mutate lot; set nspd_enriched_at always. Empty list = clear NSPD fields (no match)."""
    lot.nspd_enriched_at = datetime.now(timezone.utc)
    if not features:
        lot.nspd_specified_area_sqm = None
        lot.nspd_readable_address = None
        lot.nspd_cost_value = None
        lot.nspd_centroid_latitude = None
        lot.nspd_centroid_longitude = None
        lot.nspd_card_id = None
        lot.nspd_card_type = None
        return
    extracted = extract_nspd_options_from_feature(features[0])
    lot.nspd_specified_area_sqm = extracted["nspd_specified_area_sqm"]
    lot.nspd_readable_address = extracted["nspd_readable_address"]
    lot.nspd_cost_value = extracted["nspd_cost_value"]
    lot.nspd_centroid_latitude = extracted["nspd_centroid_latitude"]
    lot.nspd_centroid_longitude = extracted["nspd_centroid_longitude"]
    lot.nspd_card_id = extracted["nspd_card_id"]
    lot.nspd_card_type = extracted["nspd_card_type"]
    merge_nspd_into_notice_fields(
        lot,
        extracted["nspd_specified_area_sqm"],
        extracted["nspd_readable_address"],
    )


def nspd_cache_is_fresh(lot: Lot) -> bool:
    if lot.nspd_enriched_at is None:
        return False
    days = settings.nspd_refresh_after_days
    if days <= 0:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return lot.nspd_enriched_at >= cutoff


def fetch_nspd_features_sync(cadastral_number: str) -> list[dict[str, Any]]:
    """HTTP only; run in thread from async ingest. Raises on transport/HTTP errors."""
    client = NspdGeoportalClient.from_settings()
    result = client.search_by_cadastral(cadastral_number)
    return list(result) if result is not None else []


def enrich_lot_from_nspd_sync(lot: Lot) -> bool:
    """
    Fetch and apply on the current thread. Returns True if enrichment was written.
    For scripts / offline tools; ingest uses maybe_enrich_lot_nspd_async instead.
    """
    if not settings.nspd_enabled:
        return False
    cad = (lot.cadastral_number or "").strip()
    if not cad or nspd_cache_is_fresh(lot):
        return False
    try:
        features = fetch_nspd_features_sync(cad)
    except Exception:
        logger.warning("NSPD request failed for lot_id=%s cad=%s", lot.id, cad, exc_info=True)
        return False
    apply_nspd_features_to_lot(lot, features)
    return True


async def maybe_enrich_lot_nspd_async(db: Session, lot: Lot, nspd_budget: list[int] | None) -> None:
    """HTTP in worker thread; apply on asyncio thread (ORM-safe)."""
    if not settings.nspd_enabled:
        return
    cad = (lot.cadastral_number or "").strip()
    if not cad:
        return
    if nspd_cache_is_fresh(lot):
        return
    if nspd_budget is not None and nspd_budget[0] <= 0:
        return
    if nspd_budget is not None:
        nspd_budget[0] -= 1

    try:
        features = await asyncio.to_thread(fetch_nspd_features_sync, cad)
    except Exception:
        logger.warning("NSPD request failed lot_id=%s cad=%s", lot.id, cad, exc_info=True)
        return
    apply_nspd_features_to_lot(lot, features)
    db.add(lot)
    db.commit()
