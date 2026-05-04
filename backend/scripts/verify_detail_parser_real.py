from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ingest.detail_parser import parse_notice_detail

DEFAULT_META_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "latest_opendata_meta.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "detail_parser_verification.json"

COVERAGE_KEYS = (
    "cadastral_number",
    "area_sqm",
    "land_category",
    "permitted_use",
    "address",
    "lot_name",
    "start_price",
)


def _pick_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("listObjects", "data", "items", "results", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _load_data_url(meta_path: Path) -> str:
    if not meta_path.exists():
        raise FileNotFoundError(
            f"Meta file not found: {meta_path}. Run scripts/fetch_latest_opendata.py first."
        )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    data_url = meta.get("data_url")
    if not isinstance(data_url, str) or not data_url:
        raise RuntimeError(f"Meta file does not contain valid data_url: {meta_path}")
    return data_url


def _is_land_plot(parsed: dict[str, Any]) -> bool:
    """Heuristic: distinguish land-plot lots from buildings/concessions/water-use.

    Used to compute honest coverage only across the segment where land fields
    are expected to be filled.
    """
    land_category = (parsed.get("land_category") or "").strip().lower()
    lot_name = (parsed.get("lot_name") or "").strip().lower()
    if land_category.startswith("земли"):
        return True
    if "земельн" in lot_name:
        return True
    return False


def _field_coverage(results: list[dict[str, Any]]) -> dict[str, int]:
    coverage: dict[str, int] = {}
    for key in COVERAGE_KEYS:
        coverage[key] = sum(
            1 for row in results if (row.get("parsed") or {}).get(key) not in (None, "")
        )
    return coverage


def _empty_segment_bucket() -> dict[str, int]:
    bucket: dict[str, int] = {"_total": 0}
    for key in COVERAGE_KEYS:
        bucket[key] = 0
    return bucket


def _coverage_by_segment(
    results: list[dict[str, Any]], segment_fn
) -> dict[str, dict[str, int]]:
    """Returns {segment_value: {field: hits, ..., '_total': count}}."""
    by_seg: dict[str, dict[str, int]] = {}
    for row in results:
        parsed = row.get("parsed") or {}
        seg = str(segment_fn(parsed))
        bucket = by_seg.setdefault(seg, _empty_segment_bucket())
        bucket["_total"] += 1
        for key in COVERAGE_KEYS:
            if parsed.get(key) not in (None, ""):
                bucket[key] += 1
    return by_seg


def _segmented_coverage(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute land-plot vs other segmentation + per-land_category breakdown."""
    by_is_land = _coverage_by_segment(results, _is_land_plot)
    by_land_category = _coverage_by_segment(
        results, lambda p: (p.get("land_category") or "<unknown>").strip() or "<unknown>"
    )
    by_lot_name = _coverage_by_segment(
        results, lambda p: (p.get("lot_name") or "<unknown>").strip() or "<unknown>"
    )
    return {
        "by_is_land_plot": {"true": by_is_land.get("True", _empty_segment_bucket()),
                            "false": by_is_land.get("False", _empty_segment_bucket())},
        "by_land_category": by_land_category,
        "by_lot_name": by_lot_name,
    }


def _top_level_string_keys(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(k for k, v in payload.items() if isinstance(v, str))


async def _fetch_detail_with_retry(
    client: httpx.AsyncClient, href: str, *, retries: int, backoff_sec: float
) -> Any:
    attempts = max(1, retries + 1)
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await client.get(href)
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < attempts - 1:
                await asyncio.sleep(backoff_sec)
                continue
            raise last_exc


async def _verify(
    *,
    data_url: str | None,
    data_file: Path | None,
    limit: int,
    document_type: str | None,
    href_contains: str | None,
    sample_output: Path | None,
    retries: int,
    retry_backoff_sec: float,
) -> dict[str, Any]:
    if data_file is not None:
        payload = json.loads(data_file.read_text(encoding="utf-8"))
        items = _pick_items(payload)
        report_data_url = f"file://{data_file.resolve().as_posix()}"
    else:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            payload = (await client.get(data_url)).json()
            items = _pick_items(payload)
        report_data_url = data_url or ""

    picked: list[tuple[str, str | None, str | None]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        href = item.get("href")
        if not isinstance(href, str) or not href.startswith("http"):
            continue
        if document_type and item.get("documentType") != document_type:
            continue
        if href_contains and href_contains not in href:
            continue
        picked.append((href, item.get("documentType"), item.get("regNum")))
        if len(picked) >= limit:
            break

    results: list[dict[str, Any]] = []
    sample_saved_path: str | None = None
    sample_top_level_keys: list[str] = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for href, row_document_type, reg_num in picked:
            row: dict[str, Any] = {"href": href, "document_type": row_document_type, "reg_num": reg_num}
            try:
                detail_payload = await _fetch_detail_with_retry(
                    client, href, retries=retries, backoff_sec=retry_backoff_sec
                )
                parsed = parse_notice_detail(detail_payload)
                if sample_output and sample_saved_path is None:
                    sample_output.parent.mkdir(parents=True, exist_ok=True)
                    sample_output.write_text(
                        json.dumps(detail_payload, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    sample_saved_path = str(sample_output)
                    sample_top_level_keys = _top_level_string_keys(detail_payload)
                row["parsed"] = parsed
                row["error"] = None
            except Exception as exc:  # noqa: BLE001
                row["parsed"] = {}
                row["error"] = str(exc)
            results.append(row)

    coverage = _field_coverage(results)
    ok = [r for r in results if not r.get("error")]
    return {
        "data_url": report_data_url,
        "requested_limit": limit,
        "document_type_filter": document_type,
        "href_contains_filter": href_contains,
        "fetched_details": len(results),
        "successful_details": len(ok),
        "failed_details": len(results) - len(ok),
        "field_coverage": coverage,
        "segmented_coverage": _segmented_coverage(results),
        "sample_saved_path": sample_saved_path,
        "sample_top_level_string_keys": sample_top_level_keys,
        "results": results,
    }


def _reanalyze_existing(report_path: Path) -> dict[str, Any]:
    """Re-read an existing verification report and recompute (segmented) coverage.

    Useful for purely offline analysis when network to torgi is unavailable -
    we still have parsed results from previous successful runs.
    """
    raw = json.loads(report_path.read_text(encoding="utf-8"))
    results = raw.get("results") or []
    coverage = _field_coverage(results)
    ok = [r for r in results if not r.get("error")]
    return {
        "data_url": raw.get("data_url"),
        "requested_limit": raw.get("requested_limit"),
        "document_type_filter": raw.get("document_type_filter"),
        "href_contains_filter": raw.get("href_contains_filter"),
        "fetched_details": len(results),
        "successful_details": len(ok),
        "failed_details": len(results) - len(ok),
        "field_coverage": coverage,
        "segmented_coverage": _segmented_coverage(results),
        "sample_saved_path": raw.get("sample_saved_path"),
        "sample_top_level_string_keys": raw.get("sample_top_level_string_keys") or [],
        "results": results,
        "reanalyzed_from": str(report_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Верифицировать detail_parser на реальных notice-detail JSON из ГИС Торги."
    )
    parser.add_argument("--meta-path", default=str(DEFAULT_META_PATH))
    parser.add_argument("--data-url", default="")
    parser.add_argument(
        "--data-file",
        default="",
        help="Локальный путь к data-*.json вместо --data-url (нужно при VPN-on).",
    )
    parser.add_argument(
        "--reanalyze",
        default="",
        help="Путь к существующему report.json - пересчитать coverage без сети.",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--document-type", default="notice")
    parser.add_argument("--href-contains", default="/docs/notice_")
    parser.add_argument("--sample-output", default="")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Сколько повторов на единичный детальный fetch при сетевом сбое.",
    )
    parser.add_argument("--retry-backoff-sec", type=float, default=1.5)
    args = parser.parse_args()

    if args.reanalyze.strip():
        report = _reanalyze_existing(Path(args.reanalyze))
    else:
        data_file = Path(args.data_file) if args.data_file.strip() else None
        if data_file is None:
            data_url = args.data_url.strip() or _load_data_url(Path(args.meta_path))
        else:
            data_url = args.data_url.strip() or None
        sample_output = Path(args.sample_output) if args.sample_output.strip() else None
        report = asyncio.run(
            _verify(
                data_url=data_url,
                data_file=data_file,
                limit=args.limit,
                document_type=args.document_type.strip() or None,
                href_contains=args.href_contains.strip() or None,
                sample_output=sample_output,
                retries=args.retries,
                retry_backoff_sec=args.retry_backoff_sec,
            )
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    seg = report.get("segmented_coverage", {})
    is_land = (seg.get("by_is_land_plot") or {}).get("true") or {}
    not_land = (seg.get("by_is_land_plot") or {}).get("false") or {}

    print("Detail parser verification report:")
    print(f"- data_url: {report['data_url']}")
    print(f"- fetched/success: {report['fetched_details']}/{report['successful_details']}")
    print(f"- coverage (overall): {report['field_coverage']}")
    print(
        f"- coverage (is_land_plot=true, n={is_land.get('_total', 0)}): "
        f"cadastral={is_land.get('cadastral_number', 0)}, area_sqm={is_land.get('area_sqm', 0)}, "
        f"permitted_use={is_land.get('permitted_use', 0)}, start_price={is_land.get('start_price', 0)}"
    )
    print(
        f"- coverage (is_land_plot=false, n={not_land.get('_total', 0)}): "
        f"cadastral={not_land.get('cadastral_number', 0)}, area_sqm={not_land.get('area_sqm', 0)}, "
        f"permitted_use={not_land.get('permitted_use', 0)}, start_price={not_land.get('start_price', 0)}"
    )
    print(f"- output: {output_path}")


if __name__ == "__main__":
    main()
