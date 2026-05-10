"""Resolve PKK/NSPD map URL with selectedCard via live geoportal search (lot detail only)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import settings
from app.models import Lot
from app.services.external_lot_links import nspd_lot_map_url, nspd_map_url
from app.services.map_anchor import lot_map_display_coordinates
from app.services.nspd.enrich import extract_nspd_options_from_feature, fetch_nspd_features_sync

logger = logging.getLogger(__name__)

_PKK_CACHE_TTL_SEC = 3600.0
_pkk_resolve_cache: dict[str, tuple[float, str]] = {}


def _normalize_cad_key(cadastral_number: str) -> str:
    return "".join(c for c in (cadastral_number or "") if c not in " \t\u00a0")


def _cache_get(cad_key: str) -> str | None:
    if not cad_key:
        return None
    entry = _pkk_resolve_cache.get(cad_key)
    if not entry:
        return None
    expires_at, url = entry
    if time.monotonic() > expires_at:
        del _pkk_resolve_cache[cad_key]
        return None
    return url


def _cache_set(cad_key: str, url: str) -> None:
    if cad_key and url:
        _pkk_resolve_cache[cad_key] = (time.monotonic() + _PKK_CACHE_TTL_SEC, url)


def _feature_contains_cadastral(feature: dict[str, Any], cad_norm: str) -> bool:
    if not cad_norm:
        return False
    try:
        blob = _normalize_cad_key(json.dumps(feature, ensure_ascii=False))
    except (TypeError, ValueError):
        return False
    return cad_norm in blob


def _pick_feature(features: list[dict[str, Any]], cadastral_number: str) -> dict[str, Any] | None:
    if not features:
        return None
    cad_norm = _normalize_cad_key(cadastral_number)
    if cad_norm:
        for f in features:
            if isinstance(f, dict) and _feature_contains_cadastral(f, cad_norm):
                return f
    first = features[0]
    return first if isinstance(first, dict) else None


def _lot_already_has_selected_card_deep_link(lot: Lot) -> bool:
    if not (lot.nspd_card_id and lot.nspd_card_type):
        return False
    return lot_map_display_coordinates(lot) is not None


def try_build_pkk_deep_link_from_geoportal(lot: Lot) -> str | None:
    """Return map URL with selectedCard if geoportal returns a usable feature; else None."""
    if not settings.nspd_enabled or not settings.nspd_resolve_pkk_link_on_detail:
        return None
    cad = (lot.cadastral_number or "").strip()
    if not cad:
        return None

    cad_key = _normalize_cad_key(cad)
    cached = _cache_get(cad_key)
    if cached is not None:
        return cached

    try:
        features = fetch_nspd_features_sync(cad)
    except Exception:
        logger.warning("NSPD geoportal fetch failed for PKK resolve cad=%s", cad, exc_info=True)
        return None

    feature = _pick_feature(list(features or []), cad)
    if not feature:
        return None

    extracted = extract_nspd_options_from_feature(feature)
    lat = extracted.get("nspd_centroid_latitude")
    lon = extracted.get("nspd_centroid_longitude")
    card_id = extracted.get("nspd_card_id")
    card_type = extracted.get("nspd_card_type")
    if lat is None or lon is None or not card_id or not card_type:
        return None

    url = nspd_map_url(
        cad,
        centroid_latitude=float(lat),
        centroid_longitude=float(lon),
        card_id=str(card_id),
        card_type=str(card_type),
    )
    if url and "selectedCard=" in url:
        _cache_set(cad_key, url)
    return url


def pkk_lot_map_url_for_detail(lot: Lot) -> str | None:
    """PKK/NSPD URL for GET /api/lots/{id}: prefer selectedCard via DB or live geoportal."""
    if _lot_already_has_selected_card_deep_link(lot):
        return nspd_lot_map_url(lot)

    resolved = try_build_pkk_deep_link_from_geoportal(lot)
    if resolved:
        return resolved

    return nspd_lot_map_url(lot)
