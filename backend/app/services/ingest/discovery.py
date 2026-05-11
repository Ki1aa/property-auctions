from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DATA_FILE_RE = re.compile(
    r"(?P<base>https?://[^\s\"'<>]+/)"
    r"data-(?P<from>\d{8}T\d{4})-(?P<to>\d{8}T\d{4})-structure-(?P<schema>\d+)\.json",
    re.IGNORECASE,
)
_DIRECT_DATASET_LINK_RE = re.compile(
    r"https?://[^\s\"'<>]+/data-\d{8}T\d{4}-\d{8}T\d{4}-structure-\d+\.json",
    re.IGNORECASE,
)
_HREF_JSON_RE = re.compile(r"""href=["']([^"']+\.json(?:\?[^"']*)?)["']""", re.IGNORECASE)
_OPEN_DATA_FIELD_RE = re.compile(
    r"Гиперссылка\s*\(URL\)\s*на\s*открытые\s*данные.*?(https?://[^\s\"'<>]+\.json)",
    re.IGNORECASE | re.DOTALL,
)
_STRUCTURE_FILE_RE = re.compile(r"structure-(?P<schema>\d+)\.json", re.IGNORECASE)


@dataclass
class DiscoveredDatasetFile:
    source_url: str
    structure_url: str | None
    data_from: datetime | None
    data_to: datetime | None
    schema_version: str | None
    source_kind: str


@dataclass
class DiscoveryPlan:
    files: list[DiscoveredDatasetFile]
    source_kind: str
    dataset_id: str
    meta_json_url: str | None = None
    discovery_error: str | None = None
    discovery_warning: str | None = None
    available_data_urls: tuple[str, ...] = ()
    attempted_urls: tuple[str, ...] = ()


@dataclass
class TorgiDiscoveryDiagnostic:
    """Structured result for scripts/tests (OpenData discovery only)."""

    meta_json_url: str | None
    dataset_id: str
    available_data_urls: list[str] = field(default_factory=list)
    available_structure_urls: list[str] = field(default_factory=list)
    selected_ingest_urls: list[str] = field(default_factory=list)
    selected_structure_urls: list[str | None] = field(default_factory=list)
    primary_ingest_url: str | None = None
    primary_structure_url: str | None = None
    error: str | None = None
    discovery_warning: str | None = None


def _parse_torgi_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _normalize_json_link(base_url: str, candidate: str) -> str:
    return urljoin(base_url, candidate.strip()).replace("&amp;", "&")


def _supported_schema_set() -> set[str]:
    return {x.strip() for x in settings.supported_structure_versions.split(",") if x.strip()}


def _build_structure_url(file_url: str, schema_version: str | None) -> str | None:
    if not schema_version:
        return None
    match = _DATA_FILE_RE.search(file_url)
    if match:
        return f"{match.group('base')}structure-{schema_version}.json"
    return None


def _parse_dataset_file_url(url: str, source_kind: str) -> DiscoveredDatasetFile:
    match = _DATA_FILE_RE.search(url)
    if not match:
        return DiscoveredDatasetFile(
            source_url=url,
            structure_url=None,
            data_from=None,
            data_to=None,
            schema_version=None,
            source_kind=source_kind,
        )
    schema_version = match.group("schema")
    return DiscoveredDatasetFile(
        source_url=url,
        structure_url=_build_structure_url(url, schema_version),
        data_from=_parse_torgi_dt(match.group("from")),
        data_to=_parse_torgi_dt(match.group("to")),
        schema_version=schema_version,
        source_kind=source_kind,
    )


async def _request_with_retries(client: httpx.AsyncClient, url: str, retries: int) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Discovery attempt %s/%s failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                await asyncio_sleep(attempt * 2)
    raise RuntimeError(f"Unable to fetch discovery URL {url}: {last_error}")


async def asyncio_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def _dataset_sort_key(entry: DiscoveredDatasetFile) -> tuple[datetime, datetime, str]:
    dt_to = entry.data_to or datetime.min.replace(tzinfo=timezone.utc)
    dt_from = entry.data_from or datetime.min.replace(tzinfo=timezone.utc)
    return dt_to, dt_from, entry.source_url


def _pick_latest(entries: list[DiscoveredDatasetFile]) -> DiscoveredDatasetFile:
    return max(entries, key=_dataset_sort_key)


def _iter_dicts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("meta", "datasets", "items", "data", "results", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _match_dataset(candidate: dict[str, Any], dataset_id: str) -> bool:
    searchable_keys = (
        "id",
        "identifier",
        "dataset_id",
        "slug",
        "identification_number",
        "registrationNumber",
    )
    lowered = dataset_id.lower()
    for key in searchable_keys:
        value = candidate.get(key)
        if isinstance(value, str) and lowered in value.lower():
            return True
    return False


def _dataset_identifier(dataset: dict[str, Any], fallback_id: str) -> str:
    for key in ("identifier", "id", "dataset_id"):
        value = dataset.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback_id


def _default_meta_json_url(dataset_id: str) -> str:
    did = dataset_id.strip()
    return f"https://torgi.gov.ru/new/opendata/{did}/meta.json"


def resolve_meta_json_url_from_dataset(dataset: dict[str, Any], dataset_id: str) -> str:
    link = dataset.get("link")
    if isinstance(link, str) and link.strip():
        return _normalize_json_link(settings.torgi_opendata_registry_url, link.strip())
    return _default_meta_json_url(_dataset_identifier(dataset, dataset_id))


def _dataset_id_from_opendata_data_url(url: str) -> str | None:
    m = re.search(r"/new/opendata/([^/]+)/data-\d{8}T\d{4}-\d{8}T\d{4}-structure-\d+\.json", url, re.I)
    return m.group(1) if m else None


def _structure_sources_by_schema(meta: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in meta.get("structure") or []:
        if not isinstance(item, dict):
            continue
        src = item.get("source")
        if not isinstance(src, str):
            continue
        m = _STRUCTURE_FILE_RE.search(src)
        if m:
            out[m.group("schema")] = src
    return out


def _format_meta_discovery_error(
    *,
    reason: str,
    meta_json_url: str,
    available_data_urls: list[str],
    attempted: list[str],
    missing_structure_for: list[str],
) -> str:
    lines = [
        reason,
        f"meta.json URL: {meta_json_url}",
        "Configure dataset via TORGI_OPENDATA_REGISTRY_URL + TORGI_OPENDATA_DATASET_ID, or set INGEST_SOURCE_URL "
        "to a fixed data-*.json URL / dataset card URL (see .env.example).",
    ]
    if available_data_urls:
        lines.append(f"data URLs listed in meta.json ({len(available_data_urls)}): " + "; ".join(available_data_urls[:40]))
        if len(available_data_urls) > 40:
            lines.append(f"... and {len(available_data_urls) - 40} more")
    else:
        lines.append("No data-*.json URLs found under meta.json[\"data\"][].source.")
    if attempted:
        lines.append("Attempted selection (not in meta or filtered out): " + "; ".join(attempted[:20]))
    if missing_structure_for:
        lines.append("Rows skipped (no matching structure-*.json in meta[\"structure\"]): " + "; ".join(missing_structure_for[:15]))
    return "\n".join(lines)


def parse_meta_dataset_to_files(
    meta: Any,
    *,
    source_kind: str,
    allowed_schemas: set[str] | None = None,
    meta_json_url: str = "",
) -> tuple[list[DiscoveredDatasetFile], list[str], list[str], str | None]:
    """Parse GIS Torgi meta.json into discovery rows.

    Returns (files, all_data_sources_from_meta, skipped_reasons, error).
    When error is set, files may be empty.
    """
    if not isinstance(meta, dict):
        return [], [], [], "meta.json root JSON is not an object"
    rows = meta.get("data")
    if not isinstance(rows, list) or not rows:
        return [], [], [], 'meta.json has no non-empty "data" array'

    struct_by_schema = _structure_sources_by_schema(meta)
    allowed = allowed_schemas if allowed_schemas is not None else _supported_schema_set()
    files: list[DiscoveredDatasetFile] = []
    all_sources: list[str] = []
    skipped: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        src = row.get("source") or row.get("url")
        if not isinstance(src, str) or not src.strip():
            continue
        if not _DATA_FILE_RE.search(src):
            continue
        all_sources.append(src.strip())
        parsed = _parse_dataset_file_url(src.strip(), source_kind)
        schema_from_row = row.get("structure")
        schema_ver = str(schema_from_row if schema_from_row is not None else parsed.schema_version or "").strip()
        if not schema_ver:
            skipped.append(f"{src}: missing structure version")
            continue
        parsed.schema_version = schema_ver
        if struct_by_schema and schema_ver in struct_by_schema:
            parsed.structure_url = struct_by_schema[schema_ver]
        else:
            built = _build_structure_url(parsed.source_url, schema_ver)
            if struct_by_schema and schema_ver not in struct_by_schema:
                skipped.append(f"{src}: structure version {schema_ver!r} not in meta[\"structure\"]")
                continue
            parsed.structure_url = built
        if allowed and parsed.schema_version and parsed.schema_version not in allowed:
            continue
        if not parsed.structure_url:
            skipped.append(f"{src}: could not resolve structure-*.json URL")
            continue
        files.append(parsed)

    if not files:
        err = _format_meta_discovery_error(
            reason="No ingestible data files after parsing meta.json (check SUPPORTED_STRUCTURE_VERSIONS and structure block).",
            meta_json_url=meta_json_url or "(unknown)",
            available_data_urls=all_sources,
            attempted=[],
            missing_structure_for=skipped,
        )
        return [], all_sources, skipped, err
    return files, all_sources, skipped, None


async def _discover_from_registry(client: httpx.AsyncClient) -> tuple[list[DiscoveredDatasetFile], str]:
    response = await _request_with_retries(client, settings.torgi_opendata_registry_url, settings.ingest_retry_count)
    payload = response.json()
    entries = _iter_dicts(payload)
    if not entries:
        raise RuntimeError("Registry payload does not contain dataset entries (expected list or meta/datasets/items)")

    dataset = next((entry for entry in entries if _match_dataset(entry, settings.torgi_opendata_dataset_id)), None)
    if dataset is None:
        raise RuntimeError(f"Dataset {settings.torgi_opendata_dataset_id!r} not found in registry")

    meta_url = resolve_meta_json_url_from_dataset(dataset, settings.torgi_opendata_dataset_id)
    meta_response = await _request_with_retries(client, meta_url, settings.ingest_retry_count)
    meta_payload = meta_response.json()
    allowed = _supported_schema_set()
    files, all_sources, skipped, err = parse_meta_dataset_to_files(
        meta_payload,
        source_kind="registry",
        allowed_schemas=allowed,
        meta_json_url=meta_url,
    )
    if err:
        detail = _format_meta_discovery_error(
            reason=err.split("\n")[0],
            meta_json_url=meta_url,
            available_data_urls=all_sources,
            attempted=[],
            missing_structure_for=skipped,
        )
        raise RuntimeError(detail)
    return files, meta_url


def _extract_dataset_url_from_card(
    html: str, card_url: str, source_kind: str = "card"
) -> list[DiscoveredDatasetFile]:
    links: list[str] = []

    preferred_match = _OPEN_DATA_FIELD_RE.search(html)
    if preferred_match:
        links.append(_normalize_json_link(card_url, preferred_match.group(1)))

    links.extend(match.group(0) for match in _DIRECT_DATASET_LINK_RE.finditer(html))

    for match in _HREF_JSON_RE.finditer(html):
        links.append(_normalize_json_link(card_url, match.group(1)))

    filtered = [url for url in links if _DATA_FILE_RE.search(url)]
    unique = list(dict.fromkeys(filtered))
    if not unique:
        raise RuntimeError("Dataset card parsed, but no valid data-*.json links were found")
    return [_parse_dataset_file_url(url, source_kind) for url in unique]


async def _discover_from_card_url(
    client: httpx.AsyncClient, card_url: str, source_kind: str = "card"
) -> tuple[list[DiscoveredDatasetFile], str]:
    response = await _request_with_retries(client, card_url, settings.ingest_retry_count)
    seed_entries = _extract_dataset_url_from_card(response.text, card_url, source_kind)
    first_url = seed_entries[0].source_url
    ds_id = _dataset_id_from_opendata_data_url(first_url)
    if not ds_id:
        raise RuntimeError(
            f"Could not derive dataset id from first data URL on card: {first_url}. "
            "Set TORGI_OPENDATA_DATASET_ID or use registry discovery."
        )
    meta_url = _default_meta_json_url(ds_id)
    meta_response = await _request_with_retries(client, meta_url, settings.ingest_retry_count)
    meta_payload = meta_response.json()
    allowed = _supported_schema_set()
    files, all_sources, skipped, err = parse_meta_dataset_to_files(
        meta_payload,
        source_kind=source_kind,
        allowed_schemas=allowed,
        meta_json_url=meta_url,
    )
    if err:
        detail = _format_meta_discovery_error(
            reason=err.split("\n")[0],
            meta_json_url=meta_url,
            available_data_urls=all_sources,
            attempted=[first_url],
            missing_structure_for=skipped,
        )
        raise RuntimeError(detail)
    return files, meta_url


async def _discover_from_card(client: httpx.AsyncClient) -> tuple[list[DiscoveredDatasetFile], str]:
    return await _discover_from_card_url(client, settings.torgi_opendata_card_url)


def _from_direct_override() -> list[DiscoveredDatasetFile]:
    if not settings.ingest_source_url:
        return []
    if not _DATA_FILE_RE.search(settings.ingest_source_url):
        return []
    file_ref = _parse_dataset_file_url(settings.ingest_source_url, "direct")
    if settings.ingest_structure_url:
        file_ref.structure_url = settings.ingest_structure_url
    return [file_ref]


def _daterange(start_date: date, end_date: date) -> list[date]:
    values: list[date] = []
    current = start_date
    while current <= end_date:
        values.append(current)
        current += timedelta(days=1)
    return values


def _replace_file_interval(template_url: str, day_from: date, day_to: date, schema_version: str | None) -> str:
    if not schema_version:
        schema_version = "20240401"
    return _DATA_FILE_RE.sub(
        lambda m: (
            f"{m.group('base')}data-{day_from.strftime('%Y%m%d')}T0000-"
            f"{day_to.strftime('%Y%m%d')}T0000-structure-{schema_version}.json"
        ),
        template_url,
    )


def _planned_dates(last_processed_to: datetime | None, mode: str) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    if mode == "backfill":
        if not settings.backfill_from:
            raise RuntimeError("BACKFILL_FROM must be set when INGEST_MODE=backfill")
        start = datetime.strptime(settings.backfill_from, "%Y-%m-%d").date()
        end = datetime.strptime(settings.backfill_to, "%Y-%m-%d").date() if settings.backfill_to else today
        return start, end

    if last_processed_to:
        start = last_processed_to.date()
    else:
        offset_day = today + timedelta(days=settings.ingest_daily_offset_days)
        start = offset_day
    if start > today:
        start = today
    return start, today


def _plan_meta_files_with_watermark(
    available: list[DiscoveredDatasetFile],
    mode: str,
    last_processed_to: datetime | None,
) -> tuple[list[DiscoveredDatasetFile], str | None, str | None]:
    """Select only URLs present in meta-derived `available`. Never synthesize new data URLs.

    Returns (files, discovery_warning, selection_error). selection_error is set when no files
    can be chosen (e.g. backfill window misses all meta slices).
    """
    if not available:
        return [], None, "No files were returned from meta.json parsing (empty data list)."

    if mode == "backfill":
        start_date, end_date = _planned_dates(None, "backfill")
        selected = [
            e
            for e in available
            if e.data_from and e.data_to and e.data_to.date() >= start_date and e.data_from.date() <= end_date
        ]
        if not selected:
            msg = (
                f"No meta.json data slices overlap backfill window {start_date}..{end_date}. "
                "See available data URLs in discovery_error / diagnostic output."
            )
            return [], None, msg
        return sorted(selected, key=_dataset_sort_key), None, None

    start_date, end_date = _planned_dates(last_processed_to, mode)
    scheduled: list[DiscoveredDatasetFile] = []
    seen: set[str] = set()
    for day in _daterange(start_date, end_date):
        next_day = day + timedelta(days=1)
        match = next(
            (
                e
                for e in available
                if e.data_from
                and e.data_to
                and e.data_from.date() == day
                and e.data_to.date() == next_day
            ),
            None,
        )
        if match and match.source_url not in seen:
            scheduled.append(match)
            seen.add(match.source_url)

    if scheduled:
        return sorted(scheduled, key=_dataset_sort_key), None, None

    fallback = _pick_latest(available)
    warn = (
        f"No daily data-*.json slice in meta.json for each calendar day in {start_date}..{end_date} "
        f"(watermark={last_processed_to!r}). Using latest available meta entry: {fallback.source_url}"
    )
    return [fallback], warn, None


def _plan_direct_files_with_watermark(
    direct: list[DiscoveredDatasetFile],
    mode: str,
    last_processed_to: datetime | None,
) -> tuple[list[DiscoveredDatasetFile], str | None]:
    """Legacy behaviour for explicit INGEST_SOURCE_URL data file: allow synthesized sibling URLs."""
    if not direct:
        return [], None
    latest = _pick_latest(direct)
    start_date, end_date = _planned_dates(last_processed_to, mode)
    scheduled: list[DiscoveredDatasetFile] = []
    if _DATA_FILE_RE.search(latest.source_url):
        for day in _daterange(start_date, end_date):
            next_day = day + timedelta(days=1)
            url = _replace_file_interval(latest.source_url, day, next_day, latest.schema_version)
            scheduled.append(_parse_dataset_file_url(url, latest.source_kind))
    else:
        scheduled.append(latest)

    if mode == "operational":
        planned = sorted({item.source_url: item for item in scheduled}.values(), key=_dataset_sort_key)
        return planned if planned else [latest], None

    by_url: dict[str, DiscoveredDatasetFile] = {item.source_url: item for item in scheduled}
    by_url.update({item.source_url: item for item in direct})
    return sorted(by_url.values(), key=_dataset_sort_key), None


async def build_discovery_plan(
    *,
    mode: str,
    last_processed_to: datetime | None,
) -> DiscoveryPlan:
    if mode == "backfill":
        _planned_dates(last_processed_to, mode)

    timeout = settings.ingest_timeout_seconds
    meta_json_url: str | None = None
    discovery_warning: str | None = None
    available_urls: tuple[str, ...] = ()
    attempted: tuple[str, ...] = ()

    async with httpx.AsyncClient(timeout=timeout) as client:
        direct = _from_direct_override()
        if direct:
            files, warn = _plan_direct_files_with_watermark(direct, mode, last_processed_to)
            return DiscoveryPlan(
                files=files,
                source_kind="direct",
                dataset_id=settings.torgi_opendata_dataset_id,
                meta_json_url=None,
                discovery_warning=warn,
            )

        override_url = (settings.ingest_source_url or "").strip()
        try:
            if override_url:
                discovered, meta_json_url = await _discover_from_card_url(client, override_url, source_kind="card_override")
                source_kind = "card_override"
            else:
                try:
                    discovered, meta_json_url = await _discover_from_registry(client)
                    source_kind = "registry"
                except Exception as registry_exc:  # noqa: BLE001
                    logger.warning("Registry discovery failed, trying card fallback: %s", registry_exc)
                    discovered, meta_json_url = await _discover_from_card(client)
                    source_kind = "card"
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            return DiscoveryPlan(
                files=[],
                source_kind="error",
                dataset_id=settings.torgi_opendata_dataset_id,
                meta_json_url=meta_json_url,
                discovery_error=msg,
            )

        files, discovery_warning, selection_error = _plan_meta_files_with_watermark(
            discovered, mode, last_processed_to
        )
        available_urls = tuple(sorted({d.source_url for d in discovered}))
        if selection_error:
            err = _format_meta_discovery_error(
                reason=selection_error,
                meta_json_url=meta_json_url or "(unknown)",
                available_data_urls=list(available_urls),
                attempted=[],
                missing_structure_for=[],
            )
            return DiscoveryPlan(
                files=[],
                source_kind=source_kind,
                dataset_id=settings.torgi_opendata_dataset_id,
                meta_json_url=meta_json_url,
                discovery_error=err,
                available_data_urls=available_urls,
            )
        if not files:
            attempted_keys = _planned_dates(last_processed_to, mode)
            attempted = (f"{attempted_keys[0]}..{attempted_keys[1]} calendar window",)
            err = _format_meta_discovery_error(
                reason="After filtering meta.json entries for the ingest window, no files remain to process.",
                meta_json_url=meta_json_url or "(unknown)",
                available_data_urls=list(available_urls),
                attempted=list(attempted),
                missing_structure_for=[],
            )
            return DiscoveryPlan(
                files=[],
                source_kind=source_kind,
                dataset_id=settings.torgi_opendata_dataset_id,
                meta_json_url=meta_json_url,
                discovery_error=err,
                available_data_urls=available_urls,
                attempted_urls=attempted,
            )

    return DiscoveryPlan(
        files=files,
        source_kind=source_kind,
        dataset_id=settings.torgi_opendata_dataset_id,
        meta_json_url=meta_json_url,
        discovery_warning=discovery_warning,
        available_data_urls=available_urls,
    )


async def run_torgi_discovery_diagnostic() -> TorgiDiscoveryDiagnostic:
    """Resolve meta.json and print-quality selection (no ingest side effects)."""
    timeout = settings.ingest_timeout_seconds
    dataset_id = settings.torgi_opendata_dataset_id
    diag = TorgiDiscoveryDiagnostic(meta_json_url=None, dataset_id=dataset_id)

    async with httpx.AsyncClient(timeout=timeout) as client:
        direct = _from_direct_override()
        if direct:
            diag.meta_json_url = None
            diag.available_data_urls = [d.source_url for d in direct]
            diag.available_structure_urls = [u for u in [d.structure_url for d in direct] if u]
            diag.primary_ingest_url = direct[0].source_url
            diag.primary_structure_url = direct[0].structure_url
            diag.selected_ingest_urls = [d.source_url for d in direct]
            diag.selected_structure_urls = [d.structure_url for d in direct]
            return diag

        override_url = (settings.ingest_source_url or "").strip()
        try:
            if override_url:
                discovered, meta_url = await _discover_from_card_url(client, override_url, source_kind="card_override")
            else:
                try:
                    discovered, meta_url = await _discover_from_registry(client)
                except Exception:
                    discovered, meta_url = await _discover_from_card(client)
        except Exception as exc:  # noqa: BLE001
            diag.error = str(exc)
            return diag

        diag.meta_json_url = meta_url
        diag.available_data_urls = sorted({d.source_url for d in discovered})
        diag.available_structure_urls = sorted({d.structure_url for d in discovered if d.structure_url})

        mode_val = (settings.ingest_mode or "operational").lower()
        files, warn, sel_err = _plan_meta_files_with_watermark(discovered, mode_val, None)
        diag.discovery_warning = warn
        if sel_err:
            diag.error = sel_err
            return diag
        if not files:
            diag.error = (
                "No file selected for current ingest mode/window. "
                f"meta has {len(diag.available_data_urls)} data URLs; check INGEST_MODE and watermark."
            )
            return diag

        diag.selected_ingest_urls = [f.source_url for f in files]
        diag.selected_structure_urls = [f.structure_url for f in files]
        diag.primary_ingest_url = files[-1].source_url
        diag.primary_structure_url = files[-1].structure_url
    return diag
