"""NSPD (nspd.gov.ru) geoportal client — optional enrichment; off by default."""

from app.services.nspd.client import NspdGeoportalClient, extract_feature_collection_items, parse_geoportal_response
from app.services.nspd.enrich import (
    apply_nspd_features_to_lot,
    enrich_lot_from_nspd_sync,
    extract_nspd_options_from_feature,
    maybe_enrich_lot_nspd_async,
    nspd_cache_is_fresh,
)

__all__ = [
    "NspdGeoportalClient",
    "apply_nspd_features_to_lot",
    "enrich_lot_from_nspd_sync",
    "extract_feature_collection_items",
    "extract_nspd_options_from_feature",
    "maybe_enrich_lot_nspd_async",
    "nspd_cache_is_fresh",
    "parse_geoportal_response",
]
