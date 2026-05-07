"""Ad-hoc: probe public HTML pages of torgi.gov.ru for sample lots
and the public search API used by the UI filters.

Saves probe report to data/raw/torgi_ui_probe_<DATE>.json
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DATE_TAG = datetime.now(timezone.utc).strftime("%Y%m%d")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PROBE_LOTS = [
    "22000172340000000706",  # Тюмень ZK ИЖС 2.1, 627 кв.м
    "21000012700000001595",  # Тюмень ZK 6.6 промышл., 27990 кв.м
    "22000050530000000755",  # estate=72/right=89 кросс-региональный
]


def _detect_spa(html: str) -> bool:
    """Torgi SPA returns mostly an empty html shell with /static/ js bundle."""
    return "<div id=\"app\"" in html or "<div id=\"root\"" in html or "window.__INITIAL_STATE__" in html


def _extract_json_blocks(html: str) -> list[dict]:
    """Extract <script type=application/json> or window.__INITIAL_STATE__ if present."""
    blocks = []
    for m in re.finditer(r"<script[^>]*type=[\"']application/json[\"'][^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE):
        try:
            blocks.append(json.loads(m.group(1)))
        except Exception:
            pass
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>", html, re.DOTALL)
    if m:
        try:
            blocks.append(json.loads(m.group(1)))
        except Exception:
            pass
    return blocks


def main() -> None:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/json,*/*"}
    out: dict = {
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "probes": {},
    }

    with httpx.Client(timeout=30, headers=headers, follow_redirects=True) as client:
        # 1. HTML cards for sample lots
        for reg in PROBE_LOTS:
            url = f"https://torgi.gov.ru/new/public/notices/view/{reg}"
            print(f"GET {url}")
            try:
                r = client.get(url)
                html = r.text
                spa = _detect_spa(html)
                json_blocks = _extract_json_blocks(html) if not spa else []
                # Heuristic content check
                contains_cad = bool(re.search(r"\b\d{1,2}:\d{1,2}:\d{6,7}:\d+\b", html))
                contains_price = "priceMin" in html or "руб" in html
                out["probes"][f"html_card_{reg}"] = {
                    "url": url,
                    "status": r.status_code,
                    "content_length": len(html),
                    "is_spa_shell": spa,
                    "html_contains_cadastral": contains_cad,
                    "html_contains_price_text": contains_price,
                    "embedded_json_blocks_found": len(json_blocks),
                    "first_500_chars": html[:500],
                }
            except Exception as exc:  # noqa: BLE001
                out["probes"][f"html_card_{reg}"] = {"url": url, "error": str(exc)}
            time.sleep(0.5)

        # 2. Lot view url variant
        url = f"https://torgi.gov.ru/new/public/lots/lot/{PROBE_LOTS[0]}/lot-info/general-info"
        print(f"GET {url}")
        try:
            r = client.get(url)
            out["probes"]["html_lot_view"] = {
                "url": url, "status": r.status_code, "content_length": len(r.text), "is_spa_shell": _detect_spa(r.text)
            }
        except Exception as exc:
            out["probes"]["html_lot_view"] = {"url": url, "error": str(exc)}
        time.sleep(0.5)

        # 3. Public notices search API (used by SPA via XHR)
        # Try common endpoints based on torgi.gov.ru new SPA conventions.
        api_probes = [
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/lotcards/search?text=&dynSubjRF=72&biddType=ZK&size=5&sort=firstVersionPublishDate,desc",
                None,
            ),
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/notices/search?dynSubjRF=72&biddType=ZK&size=5",
                None,
            ),
            # Reference dictionaries used to populate UI dropdowns
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/dict/biddType",
                None,
            ),
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/dict/landCategory",
                None,
            ),
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/dict/permittedUse",
                None,
            ),
            (
                "GET",
                "https://torgi.gov.ru/new/api/public/lotcards/byNoticeNumber/22000172340000000706",
                None,
            ),
        ]
        for method, url, body in api_probes:
            key = "api_" + url.split("/", 7)[-1].replace("/", "_").replace("?", "_")[:80]
            print(f"{method} {url}")
            try:
                if method == "GET":
                    r = client.get(url)
                else:
                    r = client.request(method, url, json=body)
                content = r.text
                ctype = r.headers.get("content-type", "")
                preview: object
                if "json" in ctype.lower():
                    try:
                        parsed = r.json()
                        if isinstance(parsed, dict):
                            preview = {
                                "keys_top": list(parsed.keys())[:15],
                                "totalElements": parsed.get("totalElements"),
                                "content_len": len(parsed.get("content") or []) if isinstance(parsed.get("content"), list) else None,
                                "sample_first_item": (parsed.get("content") or [None])[0] if isinstance(parsed.get("content"), list) else None,
                            }
                        elif isinstance(parsed, list):
                            preview = {"list_len": len(parsed), "first_item": parsed[0] if parsed else None}
                        else:
                            preview = {"value_type": type(parsed).__name__, "value": str(parsed)[:300]}
                    except Exception:
                        preview = {"raw_first_500": content[:500]}
                else:
                    preview = {"raw_first_500": content[:500]}
                out["probes"][key] = {
                    "method": method,
                    "url": url,
                    "status": r.status_code,
                    "content_type": ctype,
                    "content_length": len(content),
                    "preview": preview,
                }
            except Exception as exc:  # noqa: BLE001
                out["probes"][key] = {"method": method, "url": url, "error": str(exc)}
            time.sleep(0.5)

    out_path = ROOT / "data" / "raw" / f"torgi_ui_probe_{DATE_TAG}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path.relative_to(ROOT)}")
    print("Quick summary:")
    for k, v in out["probes"].items():
        if isinstance(v, dict):
            st = v.get("status", v.get("error", "?"))
            cl = v.get("content_length")
            print(f"  {k}: status={st} len={cl}")


if __name__ == "__main__":
    main()
