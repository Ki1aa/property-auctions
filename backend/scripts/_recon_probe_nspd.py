"""Ad-hoc: probe НСПД (nspd.gov.ru) public endpoints with cadastral numbers.

Tries several known endpoint shapes (the public NSPD search has changed paths
several times in 2024-2026). Saves results to data/raw/nspd_samples_<DATE>.json.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")
SRC_CADS = ROOT / "data" / "raw" / "_recon_cadnums_for_nspd.json"
OUT = ROOT / "data" / "raw" / f"nspd_samples_{DATE_TAG}.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Endpoint templates. {cad} will be substituted with the cadastral number.
# thematicSearchId values commonly used:
#   1 = земельные участки
#   2 = ОКС
ENDPOINT_TEMPLATES: list[tuple[str, str]] = [
    ("geoportal_v2_thematic1", "https://nspd.gov.ru/api/geoportal/v2/search/geoportal?query={cad}&thematicSearchId=1"),
    ("geoportal_v1_thematic1", "https://nspd.gov.ru/api/geoportal/v1/search/geoportal?query={cad}&thematicSearchId=1"),
    ("aeggis_v3_objects", "https://nspd.gov.ru/api/aeggis/v3/search/objects?searchString={cad}"),
    ("eggis_search", "https://nspd.gov.ru/api/eggis/v1/search?query={cad}"),
    ("rosreestr_byCad", "https://nspd.gov.ru/api/rosreestr/v1/by-cad-num/{cad}"),
]


def _summarize(payload):
    if isinstance(payload, dict):
        keys = list(payload.keys())[:20]
        # Try common geoportal response shape
        feats = payload.get("data") or payload.get("features") or payload.get("items") or payload.get("results")
        cnt = len(feats) if isinstance(feats, list) else None
        first = feats[0] if isinstance(feats, list) and feats else None
        return {"top_keys": keys, "items_count": cnt, "first_item_keys": list(first.keys())[:25] if isinstance(first, dict) else None}
    if isinstance(payload, list):
        return {"list_len": len(payload), "first_keys": list(payload[0].keys())[:25] if payload and isinstance(payload[0], dict) else None}
    return {"value_type": type(payload).__name__}


def main() -> None:
    cads = json.loads(SRC_CADS.read_text(encoding="utf-8"))
    cads = cads[:8]  # cap at 8 to stay polite
    print(f"Probing NSPD with {len(cads)} cadastral numbers across {len(ENDPOINT_TEMPLATES)} endpoint shapes\n")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "ru,en;q=0.8",
        "Referer": "https://nspd.gov.ru/",
        "Origin": "https://nspd.gov.ru",
    }

    results: dict = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint_templates": dict(ENDPOINT_TEMPLATES),
        "cadnums_probed": [c["cadnum"] for c in cads],
        "endpoint_health": {},
        "samples": [],
    }

    # Step 1: discover which endpoint actually responds — probe each with the first cadnum
    first_cad = cads[0]["cadnum"]
    print(f"Step 1: testing endpoint shapes with cad={first_cad}")
    healthy = []
    with httpx.Client(timeout=30, headers=headers, follow_redirects=True, verify=False) as client:
        for name, tmpl in ENDPOINT_TEMPLATES:
            url = tmpl.format(cad=first_cad)
            try:
                r = client.get(url)
                status = r.status_code
                ctype = r.headers.get("content-type", "")
                size = len(r.content)
                ok_json = "json" in ctype.lower() and r.status_code == 200
                results["endpoint_health"][name] = {
                    "url_template": tmpl,
                    "status": status,
                    "content_type": ctype,
                    "content_length": size,
                    "is_json_2xx": ok_json,
                }
                print(f"  {name:24} status={status} ctype={ctype[:30]:30} size={size}")
                if ok_json:
                    healthy.append((name, tmpl))
            except Exception as exc:  # noqa: BLE001
                results["endpoint_health"][name] = {"url_template": tmpl, "error": str(exc)}
                print(f"  {name:24} ERROR: {exc}")
            time.sleep(0.4)

        if not healthy:
            print("\nNo healthy NSPD endpoint found. Saving health report only.")
            OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            return

        # Step 2: hit each healthy endpoint with all cadnums (up to 8)
        print(f"\nStep 2: collecting samples from {len(healthy)} healthy endpoint(s) for {len(cads)} cadnums")
        for cad_entry in cads:
            cad = cad_entry["cadnum"]
            for name, tmpl in healthy:
                url = tmpl.format(cad=cad)
                try:
                    r = client.get(url)
                    payload = r.json() if "json" in r.headers.get("content-type", "").lower() else None
                    sample = {
                        "cadnum": cad,
                        "regNum": cad_entry["regNum"],
                        "endpoint_name": name,
                        "url": url,
                        "status": r.status_code,
                        "summary": _summarize(payload) if payload is not None else {"raw_text_first_400": r.text[:400]},
                        "raw_payload": payload,
                    }
                    results["samples"].append(sample)
                    print(f"  {cad}  {name}: status={r.status_code} items={(sample['summary'] or {}).get('items_count')}")
                except Exception as exc:  # noqa: BLE001
                    results["samples"].append({"cadnum": cad, "regNum": cad_entry["regNum"], "endpoint_name": name, "url": url, "error": str(exc)})
                    print(f"  {cad}  {name}: ERROR {exc}")
                time.sleep(0.5)

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
