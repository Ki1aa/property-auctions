"""Compare IZHS detection by code (whitelist) vs current keyword heuristic
on the saved raw notice details. Honest numbers for the report.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.ingest.detail_parser import match_izhs, split_keywords  # noqa: E402

DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")
RAW_DIR = ROOT / "data" / "raw" / f"torgi_sample_lots_full_{DATE_TAG}"
SAMPLE = ROOT / "data" / "raw" / f"torgi_sample_lots_{DATE_TAG}.json"

IZHS_CODES = {"2.1", "2.2", "2.3", "13.1", "13.2"}
DEFAULT_KEYWORDS = "ИЖС,индивидуальное жилищное строительство,для индивидуального жилого,2.1"

sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
keywords = split_keywords(DEFAULT_KEYWORDS)
print("Keywords:", keywords)

by_code = 0
by_keyword = 0
mismatches = []
for it in sample["items"]:
    reg = it["opendata_item"]["regNum"]
    raw_path = RAW_DIR / f"{reg}.json"
    if not raw_path.exists():
        continue
    detail = json.loads(raw_path.read_text(encoding="utf-8"))
    vri_codes = it.get("permitted_use_codes") or []
    code_match = any(any(c == w or c.startswith(w + ".") for w in IZHS_CODES) for c in vri_codes)
    kw_match = match_izhs(detail, keywords)
    if code_match:
        by_code += 1
    if kw_match:
        by_keyword += 1
    if code_match != kw_match:
        mismatches.append((reg, vri_codes, code_match, kw_match))

print(f"By PermittedUse.code in {sorted(IZHS_CODES)} (with prefix match): {by_code}/{len(sample['items'])}")
print(f"By current keyword match_izhs() on full detail:                  {by_keyword}/{len(sample['items'])}")
print(f"Mismatches: {len(mismatches)}")
for reg, codes, c, k in mismatches:
    print(f"  {reg}: codes={codes} code_match={c} keyword_match={k}")
