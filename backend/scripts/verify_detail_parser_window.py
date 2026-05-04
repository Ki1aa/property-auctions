from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DATA_URL_RE = re.compile(
    r"^(?P<base>https://torgi\.gov\.ru/new/opendata/[^/]+/)"
    r"data-(?P<from>\d{8}T\d{4})-(?P<to>\d{8}T\d{4})-structure-(?P<schema>\d+)\.json$"
)

DAILY_REPORT_RE = re.compile(r"^detail_parser_verification_(?P<day>\d{8})\.json$")

DEFAULT_META_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "latest_opendata_meta.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "detail_parser_window_verification.json"
DEFAULT_TMP_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

SEGMENT_KEYS = (
    "cadastral_number",
    "area_sqm",
    "land_category",
    "permitted_use",
    "address",
    "lot_name",
    "start_price",
)


def _load_latest_data_url(meta_path: Path) -> str:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    data_url = meta.get("data_url")
    if not isinstance(data_url, str) or not data_url:
        raise RuntimeError(f"Invalid data_url in {meta_path}")
    return data_url


def _build_day_url(base: str, day: datetime, schema: str) -> str:
    next_day = day + timedelta(days=1)
    return (
        f"{base}data-{day.strftime('%Y%m%d')}T0000-"
        f"{next_day.strftime('%Y%m%d')}T0000-structure-{schema}.json"
    )


def _sum_coverage(acc: dict[str, int], value: dict[str, Any]) -> None:
    for key, count in value.items():
        acc[key] = acc.get(key, 0) + int(count)


def _empty_segment_bucket() -> dict[str, int]:
    bucket = {"_total": 0}
    for key in SEGMENT_KEYS:
        bucket[key] = 0
    return bucket


def _accumulate_segment(acc: dict[str, dict[str, int]], increment: dict[str, dict[str, int]]) -> None:
    for seg_value, bucket in (increment or {}).items():
        if not isinstance(bucket, dict):
            continue
        target = acc.setdefault(seg_value, _empty_segment_bucket())
        for key, count in bucket.items():
            try:
                target[key] = target.get(key, 0) + int(count)
            except (TypeError, ValueError):
                continue


def _accumulate_window_segments(
    totals: dict[str, Any], segmented: dict[str, Any] | None
) -> None:
    if not segmented:
        return
    is_land_acc = totals.setdefault(
        "segmented_is_land_plot",
        {"true": _empty_segment_bucket(), "false": _empty_segment_bucket()},
    )
    by_is_land = segmented.get("by_is_land_plot") or {}
    for key in ("true", "false"):
        bucket = by_is_land.get(key) or {}
        for field, count in bucket.items():
            try:
                is_land_acc[key][field] = is_land_acc[key].get(field, 0) + int(count)
            except (TypeError, ValueError):
                continue
    _accumulate_segment(
        totals.setdefault("segmented_by_land_category", {}),
        segmented.get("by_land_category") or {},
    )
    _accumulate_segment(
        totals.setdefault("segmented_by_lot_name", {}),
        segmented.get("by_lot_name") or {},
    )


def _scan_local_data_files(tmp_dir: Path) -> list[Path]:
    """Find data-YYYYMMDDT0000-YYYYMMDDT0000-structure-*.json files locally."""
    return sorted(tmp_dir.glob("data-*-structure-*.json"))


def _scan_existing_daily_reports(tmp_dir: Path) -> list[tuple[str, Path]]:
    """Return [(day_str, report_path)] sorted descending by day."""
    found: list[tuple[str, Path]] = []
    for path in tmp_dir.glob("detail_parser_verification_*.json"):
        match = DAILY_REPORT_RE.match(path.name)
        if not match:
            continue
        day = match.group("day")
        found.append((day, path))
    found.sort(key=lambda pair: pair[0], reverse=True)
    return found


def _build_run_record(day_str: str, source: str, completed: subprocess.CompletedProcess[str], daily_output: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "day": day_str,
        "data_url": source,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "report_file": str(daily_output),
    }
    if completed.returncode == 0 and daily_output.exists():
        report = json.loads(daily_output.read_text(encoding="utf-8"))
        record["report_summary"] = {
            "fetched_details": report.get("fetched_details", 0),
            "successful_details": report.get("successful_details", 0),
            "failed_details": report.get("failed_details", 0),
            "field_coverage": report.get("field_coverage", {}),
            "segmented_coverage": report.get("segmented_coverage", {}),
        }
    return record


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Пакетная верификация detail_parser на окне дат по реальным notice."
    )
    parser.add_argument("--meta-path", default=str(DEFAULT_META_PATH))
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--limit-per-day", type=int, default=60)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--tmp-dir", default=str(DEFAULT_TMP_DIR))
    parser.add_argument(
        "--from-local-files",
        action="store_true",
        help="Брать data-*-structure-*.json локально из --tmp-dir, а не строить URL по latest_data_url.",
    )
    parser.add_argument(
        "--reanalyze-existing",
        action="store_true",
        help="Не запускать новые fetch, только пересчитать coverage по существующим detail_parser_verification_*.json в --tmp-dir.",
    )
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-backoff-sec", type=float, default=1.5)
    args = parser.parse_args()

    tmp_dir = Path(args.tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    day_reports: list[dict[str, Any]] = []
    totals: dict[str, Any] = {
        "requested_days": args.days,
        "processed_days": 0,
        "total_fetched_details": 0,
        "total_successful_details": 0,
        "total_failed_details": 0,
        "field_coverage_sum": {},
    }

    sources_summary: list[str] = []

    if args.reanalyze_existing:
        existing_reports = _scan_existing_daily_reports(tmp_dir)[: args.days]
        sources_summary.extend(str(report) for _, report in existing_reports)

        for day, report_path in existing_reports:
            day_str = f"{day[0:4]}-{day[4:6]}-{day[6:8]}"
            output_path = tmp_dir / f"detail_parser_verification_{day}_offline.json"

            cmd = [
                sys.executable,
                "scripts/verify_detail_parser_real.py",
                "--reanalyze",
                str(report_path),
                "--output",
                str(output_path),
            ]
            completed = subprocess.run(cmd, capture_output=True, text=True)
            record = _build_run_record(day_str, str(report_path), completed, output_path)
            if "report_summary" in record:
                totals["processed_days"] += 1
                summary = record["report_summary"]
                totals["total_fetched_details"] += int(summary.get("fetched_details", 0))
                totals["total_successful_details"] += int(summary.get("successful_details", 0))
                totals["total_failed_details"] += int(summary.get("failed_details", 0))
                _sum_coverage(totals["field_coverage_sum"], summary.get("field_coverage", {}))
                _accumulate_window_segments(totals, summary.get("segmented_coverage"))
            day_reports.append(record)

    elif args.from_local_files:
        local_files = _scan_local_data_files(tmp_dir)[: args.days]
        sources_summary.extend(str(p) for p in local_files)

        for path in local_files:
            match = re.search(r"data-(\d{8})T", path.name)
            day_str = (
                f"{match.group(1)[0:4]}-{match.group(1)[4:6]}-{match.group(1)[6:8]}"
                if match else path.stem
            )
            day_compact = match.group(1) if match else path.stem
            daily_output = tmp_dir / f"detail_parser_verification_{day_compact}.json"

            cmd = [
                sys.executable,
                "scripts/verify_detail_parser_real.py",
                "--data-file",
                str(path),
                "--limit",
                str(args.limit_per_day),
                "--document-type",
                "notice",
                "--href-contains",
                "/docs/notice_",
                "--retries",
                str(args.retries),
                "--retry-backoff-sec",
                str(args.retry_backoff_sec),
                "--output",
                str(daily_output),
            ]
            completed = subprocess.run(cmd, capture_output=True, text=True)
            record = _build_run_record(day_str, str(path), completed, daily_output)
            if "report_summary" in record:
                totals["processed_days"] += 1
                summary = record["report_summary"]
                totals["total_fetched_details"] += int(summary.get("fetched_details", 0))
                totals["total_successful_details"] += int(summary.get("successful_details", 0))
                totals["total_failed_details"] += int(summary.get("failed_details", 0))
                _sum_coverage(totals["field_coverage_sum"], summary.get("field_coverage", {}))
                _accumulate_window_segments(totals, summary.get("segmented_coverage"))
            day_reports.append(record)

    else:
        latest_url = _load_latest_data_url(Path(args.meta_path))
        sources_summary.append(latest_url)
        match = DATA_URL_RE.match(latest_url)
        if not match:
            raise RuntimeError(f"Cannot parse latest data URL: {latest_url}")

        base = match.group("base")
        schema = match.group("schema")
        latest_day = datetime.strptime(match.group("from"), "%Y%m%dT%H%M").replace(tzinfo=timezone.utc)

        for idx in range(args.days):
            day = latest_day - timedelta(days=idx)
            data_url = _build_day_url(base, day, schema)
            daily_output = tmp_dir / f"detail_parser_verification_{day.strftime('%Y%m%d')}.json"

            cmd = [
                sys.executable,
                "scripts/verify_detail_parser_real.py",
                "--data-url",
                data_url,
                "--limit",
                str(args.limit_per_day),
                "--document-type",
                "notice",
                "--href-contains",
                "/docs/notice_",
                "--retries",
                str(args.retries),
                "--retry-backoff-sec",
                str(args.retry_backoff_sec),
                "--output",
                str(daily_output),
            ]
            completed = subprocess.run(cmd, capture_output=True, text=True)
            record = _build_run_record(day.strftime("%Y-%m-%d"), data_url, completed, daily_output)
            if "report_summary" in record:
                totals["processed_days"] += 1
                summary = record["report_summary"]
                totals["total_fetched_details"] += int(summary.get("fetched_details", 0))
                totals["total_successful_details"] += int(summary.get("successful_details", 0))
                totals["total_failed_details"] += int(summary.get("failed_details", 0))
                _sum_coverage(totals["field_coverage_sum"], summary.get("field_coverage", {}))
                _accumulate_window_segments(totals, summary.get("segmented_coverage"))
            day_reports.append(record)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "days": args.days,
            "limit_per_day": args.limit_per_day,
            "from_local_files": args.from_local_files,
            "reanalyze_existing": args.reanalyze_existing,
            "sources": sources_summary,
        },
        "totals": totals,
        "days": day_reports,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    is_land_total = (totals.get("segmented_is_land_plot") or {}).get("true") or {}
    not_land_total = (totals.get("segmented_is_land_plot") or {}).get("false") or {}
    print("Window verification report:")
    print(f"- mode: {'reanalyze' if args.reanalyze_existing else ('local-files' if args.from_local_files else 'live')}")
    print(f"- processed days: {totals['processed_days']}/{args.days}")
    print(
        f"- total fetched/success/failed: "
        f"{totals['total_fetched_details']}/{totals['total_successful_details']}/{totals['total_failed_details']}"
    )
    print(f"- field coverage sum: {totals['field_coverage_sum']}")
    print(
        f"- is_land_plot=true sum (n={is_land_total.get('_total', 0)}): "
        f"cadastral={is_land_total.get('cadastral_number', 0)}, area_sqm={is_land_total.get('area_sqm', 0)}, "
        f"permitted_use={is_land_total.get('permitted_use', 0)}, start_price={is_land_total.get('start_price', 0)}"
    )
    print(
        f"- is_land_plot=false sum (n={not_land_total.get('_total', 0)}): "
        f"cadastral={not_land_total.get('cadastral_number', 0)}, area_sqm={not_land_total.get('area_sqm', 0)}, "
        f"permitted_use={not_land_total.get('permitted_use', 0)}, start_price={not_land_total.get('start_price', 0)}"
    )
    print(f"- output: {output_path}")


if __name__ == "__main__":
    main()
