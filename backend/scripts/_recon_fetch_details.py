"""Ad-hoc: fetch notice detail JSON for sampled hrefs and run them through detail_parser.

One-off reconnaissance helper. Does not write to DB. Saves:
- data/raw/torgi_sample_lots_full_<DATE>/<regNum>.json  raw notice detail
- data/raw/torgi_sample_lots_<DATE>.json                 enriched summary

Usage: python backend/scripts/_recon_fetch_details.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# Re-use the project's detail parser to keep coverage measurement honest.
from app.services.ingest.detail_parser import parse_notice_detail  # noqa: E402

SAMPLE_FILE = ROOT / "data" / "raw" / "_sample_hrefs_tmp.json"
DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")
RAW_DIR = ROOT / "data" / "raw" / f"torgi_sample_lots_full_{DATE_TAG}"
OUT_FILE = ROOT / "data" / "raw" / f"torgi_sample_lots_{DATE_TAG}.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _find_first_dict(payload, key_lower: str):
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        for k, v in node.items():
            if k.lower() == key_lower:
                return v
    return None


def _find_subject_rf_code(payload):
    """biddingObjectInfo.subjectRF.code (region code where land is located)."""
    sr = _find_first_dict(payload, "subjectrf")
    if isinstance(sr, dict):
        c = sr.get("code")
        if isinstance(c, (str, int)):
            return str(c)
    return None


def _find_municipality(payload):
    """Best-effort: pick FIAS hierarchy levels 3 (район) or 4 (поселение)."""
    fias = _find_first_dict(payload, "addressbyfias")
    if not isinstance(fias, dict):
        return None
    parts = []
    main = fias.get("name")
    h = fias.get("hierarchyObjects") or []
    if isinstance(h, list):
        for ho in h:
            if isinstance(ho, dict):
                lvl = (ho.get("level") or {}).get("code")
                if isinstance(lvl, int) and lvl in (1, 2, 3, 4) and ho.get("name"):
                    parts.append(ho["name"])
    if main:
        parts.append(main)
    return ", ".join(parts) if parts else None


def _find_permitted_use_code(payload):
    """Look up the *code* under characteristics[code=PermittedUse].characteristicValue[].code."""
    for node in _walk(payload):
        if not isinstance(node, dict):
            continue
        chars = node.get("characteristics")
        if not isinstance(chars, list):
            continue
        for ch in chars:
            if not isinstance(ch, dict):
                continue
            if str(ch.get("code", "")).lower() != "permitteduse":
                continue
            cv = ch.get("characteristicValue")
            if isinstance(cv, list):
                codes = [str(x.get("code")) for x in cv if isinstance(x, dict) and x.get("code")]
                if codes:
                    return codes
            if isinstance(cv, dict) and cv.get("code"):
                return [str(cv["code"])]
    return []


def _find_lot_status(payload):
    for node in _walk(payload):
        if isinstance(node, dict) and "lotStatus" in node and isinstance(node.get("lotStatus"), str):
            return node["lotStatus"]
    return None


def _find_bidd_dates(payload):
    bc = _find_first_dict(payload, "biddconditions")
    if isinstance(bc, dict):
        return {
            "biddStartTime": bc.get("biddStartTime"),
            "biddEndTime": bc.get("biddEndTime"),
            "biddReviewDate": bc.get("biddReviewDate"),
            "startDate": bc.get("startDate"),
        }
    return None


def _find_organizer(payload):
    bo = _find_first_dict(payload, "bidderorg")
    if isinstance(bo, dict):
        oi = bo.get("orgInfo") or {}
        if isinstance(oi, dict):
            return {
                "code": oi.get("code"),
                "name": oi.get("name"),
                "INN": oi.get("INN"),
                "KPP": oi.get("KPP"),
                "OGRN": oi.get("OGRN"),
                "orgType": oi.get("orgType"),
            }
    return None


def _find_common_info(payload):
    ci = _find_first_dict(payload, "commoninfo")
    if isinstance(ci, dict):
        bt = ci.get("biddType") or {}
        bf = ci.get("biddForm") or {}
        etp = ci.get("etp") or {}
        return {
            "noticeNumber": ci.get("noticeNumber"),
            "biddTypeCode": bt.get("code") if isinstance(bt, dict) else None,
            "biddTypeName": bt.get("name") if isinstance(bt, dict) else None,
            "biddFormCode": bf.get("code") if isinstance(bf, dict) else None,
            "biddFormName": bf.get("name") if isinstance(bf, dict) else None,
            "publishDate": ci.get("publishDate"),
            "procedureName": ci.get("procedureName"),
            "etpCode": etp.get("code") if isinstance(etp, dict) else None,
            "etpName": etp.get("name") if isinstance(etp, dict) else None,
            "ui_href": ci.get("href"),
        }
    return None


def main() -> None:
    samples = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    enriched = []
    coverage = {
        "cadastral_number": 0,
        "area_sqm": 0,
        "land_category": 0,
        "permitted_use_text": 0,
        "permitted_use_code": 0,
        "address": 0,
        "start_price": 0,
        "lot_name": 0,
        "subjectRF_code": 0,
        "municipality_fias": 0,
        "lot_status": 0,
        "bidd_dates": 0,
        "organizer": 0,
        "ui_href": 0,
    }
    fetched_ok = 0
    fetched_failed = []

    with httpx.Client(timeout=30, headers=headers, follow_redirects=True) as client:
        for idx, item in enumerate(samples, 1):
            href = item["href"]
            reg = item["regNum"]
            print(f"[{idx}/{len(samples)}] GET {reg}  {href[:80]}...")
            try:
                resp = client.get(href)
                resp.raise_for_status()
                detail = resp.json()
            except Exception as exc:  # noqa: BLE001
                print(f"  FAILED: {exc}")
                fetched_failed.append({"regNum": reg, "href": href, "error": str(exc)})
                time.sleep(0.5)
                continue
            fetched_ok += 1

            (RAW_DIR / f"{reg}.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            parsed = parse_notice_detail(detail)
            ci = _find_common_info(detail)
            organizer = _find_organizer(detail)
            sub_rf = _find_subject_rf_code(detail)
            muni = _find_municipality(detail)
            vri_codes = _find_permitted_use_code(detail)
            lot_status = _find_lot_status(detail)
            bidd = _find_bidd_dates(detail)
            ui_href = (ci or {}).get("ui_href")

            entry = {
                "opendata_item": item,
                "common_info": ci,
                "lot_status": lot_status,
                "subjectRF_code_in_detail": sub_rf,
                "municipality_fias_path": muni,
                "permitted_use_codes": vri_codes,
                "bidd_dates": bidd,
                "organizer": organizer,
                "parsed_by_detail_parser": parsed,
                "ui_href": ui_href,
            }
            enriched.append(entry)

            for k, present in [
                ("cadastral_number", bool(parsed.get("cadastral_number"))),
                ("area_sqm", parsed.get("area_sqm") is not None),
                ("land_category", bool(parsed.get("land_category"))),
                ("permitted_use_text", bool(parsed.get("permitted_use"))),
                ("permitted_use_code", bool(vri_codes)),
                ("address", bool(parsed.get("address"))),
                ("start_price", parsed.get("start_price") is not None),
                ("lot_name", bool(parsed.get("lot_name"))),
                ("subjectRF_code", bool(sub_rf)),
                ("municipality_fias", bool(muni)),
                ("lot_status", bool(lot_status)),
                ("bidd_dates", bool(bidd and any(bidd.values()))),
                ("organizer", bool(organizer)),
                ("ui_href", bool(ui_href)),
            ]:
                if present:
                    coverage[k] += 1

            time.sleep(0.3)  # gentle pacing

    summary = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset_id": "7710568760-notice",
        "source_dataset_card_url": "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275",
        "schema_version": "20240401",
        "raw_dir": str(RAW_DIR.relative_to(ROOT)),
        "selection_criteria": "subjectEstateCode==72 OR subjectRightHolderCode==72; documentType=notice (12 ZK + 3 non-ZK + 1 noticeCancel)",
        "fetched_total": len(samples),
        "fetched_ok": fetched_ok,
        "fetched_failed": fetched_failed,
        "coverage_counts": coverage,
        "coverage_percent": {k: round(100 * v / max(1, fetched_ok), 1) for k, v in coverage.items()},
        "items": enriched,
    }
    OUT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(enriched)} enriched lots to {OUT_FILE.relative_to(ROOT)}")
    print(f"Saved raw details to {RAW_DIR.relative_to(ROOT)}/")
    print(f"Coverage (n={fetched_ok}):")
    for k, v in coverage.items():
        print(f"  {k:24} {v:3}/{fetched_ok}  {summary['coverage_percent'][k]:5}%")


if __name__ == "__main__":
    main()
