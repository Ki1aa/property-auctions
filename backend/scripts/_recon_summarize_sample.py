"""Ad-hoc: print human-readable summary of the sampled Tyumen lots.

Used to produce the 10-20 lot table for source_discovery_<DATE>.md.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")
SRC = ROOT / "data" / "raw" / f"torgi_sample_lots_{DATE_TAG}.json"

IZHS_CODES = {"2.1", "2.2", "2.3", "13.1", "13.2"}  # ИЖС/малоэтажная/блокированная/огород/сад

data = json.loads(SRC.read_text(encoding="utf-8"))
items = data["items"]
print(f"sample summary ({len(items)} lots)\n")

vri_counter = Counter()
land_cat_counter = Counter()
estate_vs_right = Counter()
biddtype_counter = Counter()
izhs_count = 0
for it in items:
    vri_codes = it.get("permitted_use_codes") or []
    for c in vri_codes:
        vri_counter[c] += 1
    p = it["parsed_by_detail_parser"]
    if p.get("land_category"):
        land_cat_counter[p["land_category"]] += 1
    od = it["opendata_item"]
    estate_vs_right[(od.get("subjectEstateCode"), od.get("subjectRightHolderCode"))] += 1
    biddtype_counter[od.get("biddTypeCode")] += 1
    if any(c in IZHS_CODES for c in vri_codes):
        izhs_count += 1

print("ВРИ-коды (PermittedUse.code):", dict(vri_counter))
print("land_category:", dict(land_cat_counter))
print("estate/right pairs:", dict(estate_vs_right))
print("biddType:", dict(biddtype_counter))
print(f"ИЖС-кандидатов по белому списку {sorted(IZHS_CODES)}: {izhs_count}/{len(items)}")
print()

print("Подробная таблица:")
print()
hdr = (
    "regNum",
    "biddType",
    "estate",
    "right",
    "lotStatus",
    "category",
    "vri_code",
    "area_sqm",
    "cadastral",
    "start_price",
    "munic",
)
fmt = "  ".join(["{:<22}", "{:<10}", "{:<6}", "{:<6}", "{:<10}", "{:<28}", "{:<14}", "{:>10}", "{:<22}", "{:>14}", "{}"])
print(fmt.format(*hdr))
for it in items:
    od = it["opendata_item"]
    p = it["parsed_by_detail_parser"]
    vc = ",".join(it.get("permitted_use_codes") or []) or "-"
    cat = (p.get("land_category") or "")[:28]
    munic = (it.get("municipality_fias_path") or "")[:60]
    print(
        fmt.format(
            od.get("regNum", "-"),
            od.get("biddTypeCode", "-") or "-",
            od.get("subjectEstateCode", "-") or "-",
            od.get("subjectRightHolderCode", "-") or "-",
            (it.get("lot_status") or "-")[:10],
            cat,
            vc,
            f"{p.get('area_sqm'):.0f}" if p.get("area_sqm") is not None else "-",
            (p.get("cadastral_number") or "-"),
            f"{p.get('start_price'):.2f}" if p.get("start_price") is not None else "-",
            munic,
        )
    )

# Save list of cadastral numbers for NSPD probe
cads = []
for it in items:
    c = it["parsed_by_detail_parser"].get("cadastral_number")
    if c:
        cads.append({"cadnum": c, "regNum": it["opendata_item"]["regNum"]})
out_cads = ROOT / "data" / "raw" / "_recon_cadnums_for_nspd.json"
out_cads.write_text(json.dumps(cads, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved {len(cads)} cadastral numbers for NSPD probe to {out_cads.relative_to(ROOT)}")
