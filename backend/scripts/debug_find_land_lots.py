"""Read-only diagnostic: scan latest OpenData data-*.json slices from meta.json for MVP land rows.

  cd backend
  python scripts/debug_find_land_lots.py
  python scripts/debug_find_land_lots.py --max-files 10 --max-records 5000 --detail-cap 500
  python scripts/debug_find_land_lots.py --find-region-72 --max-files 30 --detail-cap 800

No DB writes, no Telegram. Mirrors MVP path: normalize_lot -> _maybe_enrich_with_detail -> classify_normalized_lot.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.services.ingest.client import fetch_json_payload_with_meta  # noqa: E402
from app.services.ingest.detail_parser import split_keywords  # noqa: E402
from app.services.ingest.discovery import (  # noqa: E402
    DiscoveredDatasetFile,
    _dataset_sort_key,
    parse_meta_dataset_to_files,
)
from app.services.ingest.normalizer import normalize_lot  # noqa: E402
from app.services.ingest.service import (  # noqa: E402
    _is_opendata_form,
    _is_torgi_opendata_error_envelope,
    _maybe_enrich_with_detail,
    _pick_items,
)
from app.services.mvp.classify import classify_normalized_lot  # noqa: E402
from app.services.mvp.land_filter_config import land_filter_codes  # noqa: E402
from app.services.mvp.link_builder import (  # noqa: E402
    build_lot_url,
    build_notice_url,
    build_nspd_search_url,
    resolve_notice_href_from_raw,
)
from app.services.mvp.pipeline import _attach_description, _lot_number_from, _notice_number_from  # noqa: E402

_KEYS = ("biddTypeCode", "subjectEstateCode", "biddType", "biddingType", "catCode", "category", "resourceTypeUse")


def _meta_url() -> str:
    return f"https://torgi.gov.ru/new/opendata/{settings.torgi_opendata_dataset_id.strip()}/meta.json"


def _snippet(text: str | None, n: int = 100) -> str:
    if not text:
        return ""
    t = str(text).replace("\n", " ").strip()
    return t[:n] + ("..." if len(t) > n else "")


def _row_for_table(item: dict[str, Any], lot_norm: dict[str, Any], cl: dict[str, Any]) -> dict[str, Any]:
    lot0: dict[str, Any] = {}
    lots = item.get("lots")
    if isinstance(lots, list) and lots and isinstance(lots[0], dict):
        lot0 = lots[0]
    return {
        "notice_number": _notice_number_from(lot_norm),
        "lot_number": _lot_number_from(lot_norm),
        "title": _snippet(lot_norm.get("title") or item.get("noticeName"), 80),
        "description": _snippet(lot_norm.get("description"), 80),
        "catCode": str(lot0.get("catCode") or item.get("catCode") or ""),
        "category_norm": str(lot_norm.get("category") or ""),
        "biddTypeCode": str(item.get("biddTypeCode") or ""),
        "biddType": str(item.get("biddType") or lot0.get("biddType") or ""),
        "biddingType": str(item.get("biddingType") or lot0.get("biddingType") or ""),
        "resourceTypeUse": str(lot0.get("resourceTypeUse") or item.get("resourceTypeUse") or ""),
        "permitted_use": _snippet(lot_norm.get("permitted_use"), 60),
        "land_category": _snippet(lot_norm.get("land_category"), 60),
        "cadastral_number": str(lot_norm.get("cadastral_number") or ""),
        "region_code": str(lot_norm.get("region") or ""),
        "is_land": cl["is_land"],
        "signal_level": cl["signal_level"],
        "ignored_reason": cl.get("ignored_reason") or "",
    }


def _bump_field_hist(
    hist: defaultdict[str, Counter[str]],
    scope: str,
    data: dict[str, Any],
) -> None:
    for k in _KEYS:
        v = data.get(k)
        if v in (None, ""):
            continue
        hist[f"{scope}.{k}"].update([str(v).strip()[:200]])


async def _fetch_meta() -> dict[str, Any]:
    timeout = settings.ingest_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(_meta_url())
        r.raise_for_status()
        return r.json()


async def run(*, max_files: int, max_records: int) -> int:
    print("Diagnostic: MVP land rows in OpenData (read-only, no DB, no Telegram)")
    print("meta:", _meta_url())
    codes = land_filter_codes()
    print("land_filter_codes:", sorted(codes) if codes else "(empty)")
    print("ingest_fetch_notice_details:", settings.ingest_fetch_notice_details)
    print("ingest_detail_max_per_run (this run):", settings.ingest_detail_max_per_run)
    print()

    meta = await _fetch_meta()
    allowed = {x.strip() for x in settings.supported_structure_versions.split(",") if x.strip()}
    files, _, _, err = parse_meta_dataset_to_files(
        meta,
        source_kind="diag",
        allowed_schemas=allowed,
        meta_json_url=_meta_url(),
    )
    if err:
        print("meta parse error:", err)
        return 1
    if not files:
        print("No data files in meta.json")
        return 1

    files_newest_first = sorted(files, key=_dataset_sort_key, reverse=True)[:max_files]
    print(f"Scanning {len(files_newest_first)} newest data file(s) (max_files={max_files})")
    for i, f in enumerate(files_newest_first, 1):
        print(f"  [{i}] {f.source_url}")
    print()

    izhs_keywords = split_keywords(settings.izhs_keywords)
    field_hist: defaultdict[str, Counter[str]] = defaultdict(Counter)
    norm_category_ctr: Counter[str] = Counter()
    records_total = 0
    land_rows = 0
    land_examples: list[dict[str, Any]] = []
    example_keys: set[tuple[str, str, str]] = set()
    signal_ctr: Counter[str] = Counter()
    region_72_land = 0
    detail_counter = 0

    for file_ref in files_newest_first:
        if records_total >= max_records:
            print("max_records reached before next file")
            break
        print("--- file:", file_ref.source_url)
        try:
            payload, _sha = await fetch_json_payload_with_meta(file_ref.source_url)
        except Exception as exc:  # noqa: BLE001
            print("  FETCH FAIL:", exc)
            continue
        if _is_torgi_opendata_error_envelope(payload):
            print("  SKIP:", str(payload.get("error"))[:500])
            continue
        items = _pick_items(payload)
        file_recs = 0
        file_land = 0
        for item in items:
            if records_total >= max_records:
                break
            if not isinstance(item, dict) or not _is_opendata_form(item):
                continue
            lot0: dict[str, Any] = {}
            lots = item.get("lots")
            if isinstance(lots, list) and lots and isinstance(lots[0], dict):
                lot0 = lots[0]
            _bump_field_hist(field_hist, "notice", item)
            _bump_field_hist(field_hist, "lot0", lot0)

            normalized = normalize_lot(item)
            if not normalized.get("source_id"):
                continue
            records_total += 1
            file_recs += 1

            detail_counter, normalized_lots = await _maybe_enrich_with_detail(
                normalized,
                izhs_keywords=izhs_keywords,
                already_fetched=detail_counter,
            )

            for lot_norm in normalized_lots:
                _attach_description(lot_norm)
                catn = str(lot_norm.get("category") or "").strip()
                if catn:
                    norm_category_ctr[catn] += 1
                cl = classify_normalized_lot(lot_norm)
                signal_ctr[cl["signal_level"]] += 1
                if cl["is_land"] and not cl["is_ignored"]:
                    land_rows += 1
                    file_land += 1
                    if str(lot_norm.get("region") or "").strip() == "72":
                        region_72_land += 1
                    if len(land_examples) < 10:
                        row = _row_for_table(item, lot_norm, cl)
                        ek = (row["notice_number"], row["lot_number"], row["cadastral_number"])
                        if ek not in example_keys:
                            example_keys.add(ek)
                            land_examples.append(row)
        print(f"  records_in_file: {file_recs}, land_in_file: {file_land}, detail_fetches_total: {detail_counter}")

    print()
    print("=== SUMMARY ===")
    print("records_read:", records_total)
    print("land_rows (is_land and not is_ignored):", land_rows)
    print("region_72 in land_rows:", region_72_land)
    print("signal_level (per expanded lot):", dict(signal_ctr))
    print()

    print("=== HISTOGRAMS (distinct values per field) ===")
    for key in sorted(field_hist.keys()):
        c = field_hist[key]
        if c:
            print(key, dict(c.most_common(25)))
    print()
    print("normalized category (after normalize/detail), top 30:", dict(norm_category_ctr.most_common(30)))
    print()

    print("=== ZK / land filter ===")
    if not codes:
        print("No codes configured: is_land follows relaxed-empty rule in classify.py.")
    else:
        print("MVP is_land requires normalized['category'] in:", sorted(codes))
        print("normalize_lot uses first of (biddTypeCode, subjectEstateCode) as category.")
        overlap = [c for c in norm_category_ctr if c in codes]
        if not overlap:
            print("In this scan, no normalized category value matched the filter — land_rows stay 0.")
            top = [c for c, _ in norm_category_ctr.most_common(10)]
            if top:
                print("Most common normalized categories seen:", top)
            btc = field_hist.get("notice.biddTypeCode", Counter())
            sec = field_hist.get("notice.subjectEstateCode", Counter())
            if btc:
                print("Top notice.biddTypeCode:", dict(btc.most_common(15)))
            if sec:
                print("Top notice.subjectEstateCode (used if biddTypeCode empty):", dict(sec.most_common(15)))
        else:
            print("Matching categories found in scan:", overlap)

    print()
    if land_examples:
        print("=== UP TO 10 LAND EXAMPLES ===")
        cols = list(land_examples[0].keys())
        print(" | ".join(cols))
        for row in land_examples:
            print(" | ".join(str(row.get(c) or "") for c in cols))
    else:
        print("=== NO LAND ROWS IN THIS SCAN ===")

    return 0


def _urls_for_example(lot_norm: dict[str, Any], notice_number: str, lot_number: str) -> tuple[str, str, str]:
    raw = lot_norm.get("raw") if isinstance(lot_norm.get("raw"), dict) else None
    notice_url = resolve_notice_href_from_raw(raw) or build_notice_url(notice_number)
    lot_url = build_lot_url(notice_number, lot_number)
    cad = str(lot_norm.get("cadastral_number") or "").strip()
    nspd_url = build_nspd_search_url(cad) or ""
    return notice_url, lot_url, nspd_url


def _example_region_72_row(item: dict[str, Any], lot_norm: dict[str, Any], cl: dict[str, Any]) -> dict[str, Any]:
    nn = _notice_number_from(lot_norm)
    ln = _lot_number_from(lot_norm)
    notice_url, lot_url, nspd_url = _urls_for_example(lot_norm, nn, ln)
    title = str(lot_norm.get("title") or item.get("noticeName") or "").strip()
    return {
        "notice_number": nn,
        "lot_number": ln,
        "title": title[:1024],
        "cadastral_number": str(lot_norm.get("cadastral_number") or ""),
        "signal_level": cl["signal_level"],
        "notice_url": notice_url,
        "lot_url": lot_url,
        "nspd_url": nspd_url,
    }


async def run_find_region_72(*, max_files: int, max_records_per_file: int | None, detail_cap: int) -> int:
    """Scan newest meta slices until a file has land rows with region == 72. Read-only."""
    print("Diagnostic: find first OpenData slice with region 72 land (read-only, no DB, no Telegram)")
    print("meta:", _meta_url())
    codes = land_filter_codes()
    print("land_filter_codes:", sorted(codes) if codes else "(empty)")
    print("ingest_fetch_notice_details:", settings.ingest_fetch_notice_details)
    print("ingest_detail_max_per_run (this run):", detail_cap)
    print()

    meta = await _fetch_meta()
    allowed = {x.strip() for x in settings.supported_structure_versions.split(",") if x.strip()}
    files, _, _, err = parse_meta_dataset_to_files(
        meta,
        source_kind="diag",
        allowed_schemas=allowed,
        meta_json_url=_meta_url(),
    )
    if err:
        print("meta parse error:", err)
        return 1
    if not files:
        print("No data files in meta.json")
        return 1

    files_newest_first = sorted(files, key=_dataset_sort_key, reverse=True)[:max_files]
    print(f"Scanning up to {len(files_newest_first)} newest file(s) until region_72_land_count > 0")
    for i, f in enumerate(files_newest_first, 1):
        print(f"  [{i}] {f.source_url}")
    print()

    izhs_keywords = split_keywords(settings.izhs_keywords)
    detail_counter = 0

    for file_ref in files_newest_first:
        print("--- file:", file_ref.source_url)
        try:
            payload, _sha = await fetch_json_payload_with_meta(file_ref.source_url)
        except Exception as exc:  # noqa: BLE001
            print("  FETCH FAIL:", exc)
            print(
                "  URL | records_in_file | land_in_file | region_72_land_count | "
                "signal_high_72 | signal_medium_72 | signal_low_72"
            )
            print(f"  {file_ref.source_url} | 0 | 0 | 0 | 0 | 0 | 0")
            continue
        if _is_torgi_opendata_error_envelope(payload):
            err_msg = str(payload.get("error"))[:500]
            print("  SKIP:", err_msg)
            print(
                "  URL | records_in_file | land_in_file | region_72_land_count | "
                "signal_high_72 | signal_medium_72 | signal_low_72"
            )
            print(f"  {file_ref.source_url} | 0 | 0 | 0 | 0 | 0 | 0")
            continue

        items = _pick_items(payload)
        file_recs = 0
        file_land = 0
        region_72_land = 0
        sig_h72 = sig_m72 = sig_l72 = 0
        examples: list[dict[str, Any]] = []
        example_keys: set[tuple[str, str, str]] = set()

        for item in items:
            if max_records_per_file is not None and file_recs >= max_records_per_file:
                print(f"  max_records_per_file ({max_records_per_file}) reached inside file")
                break
            if not isinstance(item, dict) or not _is_opendata_form(item):
                continue

            normalized = normalize_lot(item)
            if not normalized.get("source_id"):
                continue
            file_recs += 1

            detail_counter, normalized_lots = await _maybe_enrich_with_detail(
                normalized,
                izhs_keywords=izhs_keywords,
                already_fetched=detail_counter,
            )

            for lot_norm in normalized_lots:
                _attach_description(lot_norm)
                cl = classify_normalized_lot(lot_norm)
                if not cl["is_land"] or cl["is_ignored"]:
                    continue
                file_land += 1
                if str(lot_norm.get("region") or "").strip() != "72":
                    continue
                region_72_land += 1
                sl = cl["signal_level"]
                if sl == "HIGH":
                    sig_h72 += 1
                elif sl == "MEDIUM":
                    sig_m72 += 1
                elif sl == "LOW":
                    sig_l72 += 1
                if len(examples) < 5:
                    ek = (
                        _notice_number_from(lot_norm),
                        _lot_number_from(lot_norm),
                        str(lot_norm.get("cadastral_number") or ""),
                    )
                    if ek not in example_keys:
                        example_keys.add(ek)
                        examples.append(_example_region_72_row(item, lot_norm, cl))

        print(
            "  URL | records_in_file | land_in_file | region_72_land_count | "
            "signal_high_72 | signal_medium_72 | signal_low_72"
        )
        print(
            f"  {file_ref.source_url} | {file_recs} | {file_land} | {region_72_land} | "
            f"{sig_h72} | {sig_m72} | {sig_l72}"
        )
        print(f"  detail_fetches_total (run cumulative): {detail_counter}")

        if region_72_land > 0:
            print()
            print("=== FIRST FILE WITH region_72_land_count > 0 ===")
            print(f"  {file_ref.source_url}")
            print()
            print("=== UP TO 5 EXAMPLES (region 72, land, not ignored) ===")
            cols = [
                "notice_number",
                "lot_number",
                "title",
                "cadastral_number",
                "signal_level",
                "notice_url",
                "lot_url",
                "nspd_url",
            ]
            print(" | ".join(cols))
            for row in examples:
                print(" | ".join(str(row.get(c) or "") for c in cols))
            return 0

    print()
    print("No file in this window had region_72_land_count > 0. Increase --max-files or --max-records-per-file.")
    return 2


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(description="Diagnose land lots in latest OpenData slices (read-only)")
    p.add_argument("--max-files", type=int, default=10)
    p.add_argument("--max-records", type=int, default=5000)
    p.add_argument("--detail-cap", type=int, default=500, help="Temporarily set ingest_detail_max_per_run to this value")
    p.add_argument(
        "--find-region-72",
        action="store_true",
        help="Newest-first: print per-file stats; stop at first file with Tyumen (72) land rows; print 5 examples",
    )
    p.add_argument(
        "--max-records-per-file",
        type=int,
        default=0,
        help="With --find-region-72: cap OpenData rows per file (0 = no cap)",
    )
    args = p.parse_args()
    prev = settings.ingest_detail_max_per_run
    cap = max(1, min(args.detail_cap, 10000))
    settings.ingest_detail_max_per_run = cap
    try:
        if args.find_region_72:
            per_file = None if args.max_records_per_file <= 0 else args.max_records_per_file
            raise SystemExit(asyncio.run(run_find_region_72(max_files=args.max_files, max_records_per_file=per_file, detail_cap=cap)))
        raise SystemExit(asyncio.run(run(max_files=args.max_files, max_records=args.max_records)))
    finally:
        settings.ingest_detail_max_per_run = prev


if __name__ == "__main__":
    main()
