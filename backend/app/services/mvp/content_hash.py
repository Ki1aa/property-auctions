"""Business-only content hash for MVP lots (stable JSON subset)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

BUSINESS_HASH_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "cadastral_number",
    "address",
    "area_sqm",
    "start_price",
    "status",
    "application_start",
    "application_end",
    "auction_date",
    "permitted_use",
    "land_category",
)


def business_state_from_normalized(normalized: dict[str, Any]) -> dict[str, Any]:
    return {k: normalized.get(k) for k in BUSINESS_HASH_FIELDS}


def compute_content_hash(normalized: dict[str, Any]) -> str:
    state = business_state_from_normalized(normalized)
    canonical = json.dumps(state, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def diff_business_fields(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in BUSINESS_HASH_FIELDS:
        if before.get(k) != after.get(k):
            out[k] = {"old": before.get(k), "new": after.get(k)}
    return out
