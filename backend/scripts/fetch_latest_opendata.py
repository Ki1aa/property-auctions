from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

DEFAULT_PAGE_URL = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
DEFAULT_DATASET_CODE = "7710568760-notice"
DEFAULT_STRUCTURE_VERSION = "20240401"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

DATA_LINK_RE = re.compile(
    r'href="(?P<href>/new/opendata/(?P<dataset>[^"/]+)/data-[^"]+?\.json)"',
    re.IGNORECASE,
)
STRUCTURE_LINK_RE = re.compile(
    r'href="(?P<href>/new/opendata/(?P<dataset>[^"/]+)/structure-[^"]+?\.json)"',
    re.IGNORECASE,
)
DATA_VERSION_RE = re.compile(r"data-(\d{8}T\d{4})-(\d{8}T\d{4})")


def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    with httpx.Client(timeout=30, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def pick_latest_data_link(html: str, base_url: str) -> str:
    candidates: list[tuple[datetime, str]] = []
    for match in DATA_LINK_RE.finditer(html):
        href = match.group("href")
        version_match = DATA_VERSION_RE.search(href)
        if not version_match:
            continue
        end_part = version_match.group(2)
        end_dt = datetime.strptime(end_part, "%Y%m%dT%H%M")
        candidates.append((end_dt, urljoin(base_url, href)))

    if not candidates:
        raise RuntimeError("Не найдена ссылка на data-*.json")

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def pick_structure_link(html: str, base_url: str) -> str:
    matches = list(STRUCTURE_LINK_RE.finditer(html))
    if not matches:
        raise RuntimeError("Не найдена ссылка на structure-*.json")
    return urljoin(base_url, matches[0].group("href"))


def download_json(url: str) -> dict | list:
    text = fetch_text(url)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ответ не является JSON для URL {url}") from exc


def find_latest_data_url_by_pattern(dataset_code: str, structure_version: str, days_back: int = 7) -> str:
    base = f"https://torgi.gov.ru/new/opendata/{dataset_code}"
    now = datetime.now(timezone.utc)

    for day_shift in range(1, days_back + 1):
        end_dt = (now - timedelta(days=day_shift - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        start_dt = end_dt - timedelta(days=1)
        start_part = start_dt.strftime("%Y%m%dT%H%M")
        end_part = end_dt.strftime("%Y%m%dT%H%M")

        url = f"{base}/data-{start_part}-{end_part}-structure-{structure_version}.json"
        try:
            payload = download_json(url)
            if isinstance(payload, (list, dict)):
                return url
        except Exception:  # noqa: BLE001
            continue

    raise RuntimeError(
        f"Не удалось найти актуальный data-*.json по шаблону для dataset={dataset_code} "
        f"за последние {days_back} дней"
    )


def write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скачать последний dataset JSON и structure JSON из набора открытых данных ГИС Торги."
    )
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL)
    parser.add_argument("--dataset-code", default=DEFAULT_DATASET_CODE)
    parser.add_argument("--structure-version", default=DEFAULT_STRUCTURE_VERSION)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    page_url = args.page_url
    dataset_code = args.dataset_code
    structure_version = args.structure_version
    output_dir = Path(args.output_dir)

    html = fetch_text(page_url)
    try:
        data_url = pick_latest_data_link(html, page_url)
    except RuntimeError:
        data_url = find_latest_data_url_by_pattern(dataset_code, structure_version)

    try:
        structure_url = pick_structure_link(html, page_url)
    except RuntimeError:
        structure_url = (
            f"https://torgi.gov.ru/new/opendata/{dataset_code}/structure-{structure_version}.json"
        )

    dataset_payload = download_json(data_url)
    structure_payload = download_json(structure_url)

    dataset_name = data_url.rstrip("/").split("/")[-1]
    structure_name = structure_url.rstrip("/").split("/")[-1]

    dataset_path = output_dir / dataset_name
    structure_path = output_dir / structure_name
    meta_path = output_dir / "latest_opendata_meta.json"

    write_json(dataset_path, dataset_payload)
    write_json(structure_path, structure_payload)
    write_json(
        meta_path,
        {
            "page_url": page_url,
            "data_url": data_url,
            "structure_url": structure_url,
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
            "dataset_file": str(dataset_path),
            "structure_file": str(structure_path),
        },
    )

    print("Скачано успешно:")
    print(f"- dataset:   {dataset_path}")
    print(f"- structure: {structure_path}")
    print(f"- meta:      {meta_path}")


if __name__ == "__main__":
    main()
