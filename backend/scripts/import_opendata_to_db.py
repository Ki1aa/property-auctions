from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from dateutil import parser as date_parser
from jsonschema import Draft4Validator
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import OpenDataNotice


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_structure_version(structure_path: Path) -> str | None:
    match = re.search(r"structure-(\d+)\.json$", structure_path.name)
    return match.group(1) if match else None


def import_dataset(dataset_path: Path, structure_path: Path) -> tuple[int, int, int]:
    payload = load_json(dataset_path)
    structure = load_json(structure_path)
    validator = Draft4Validator(structure)
    structure_version = detect_structure_version(structure_path)

    items = payload.get("listObjects", [])
    if not isinstance(items, list):
        raise RuntimeError("Некорректный формат data-файла: ожидается listObjects[]")

    db = SessionLocal()
    inserted = 0
    updated = 0
    invalid = 0

    try:
        for item in items:
            wrapped = {"listObjects": [item]}
            errors = sorted(validator.iter_errors(wrapped), key=lambda e: e.path)
            if errors:
                invalid += 1
                continue

            href = item.get("href")
            if not href:
                invalid += 1
                continue

            publish_date = item.get("publishDate")
            parsed_publish_date = date_parser.parse(publish_date) if publish_date else None

            existing = db.scalar(select(OpenDataNotice).where(OpenDataNotice.href == href))
            if existing is None:
                db.add(
                    OpenDataNotice(
                        reg_num=item.get("regNum", ""),
                        document_type=item.get("documentType"),
                        publish_date=parsed_publish_date,
                        href=href,
                        bidder_org_code=item.get("bidderOrgCode"),
                        right_holder_code=item.get("rightHolderCode"),
                        bidd_type_code=item.get("biddTypeCode"),
                        ownership_forms_code=item.get("ownershipFormsCode"),
                        subject_estate_code=item.get("subjectEstateCode"),
                        subject_right_holder_code=item.get("subjectRightHolderCode"),
                        payload=item,
                        structure_version=structure_version,
                    )
                )
                inserted += 1
            else:
                existing.reg_num = item.get("regNum", "")
                existing.document_type = item.get("documentType")
                existing.publish_date = parsed_publish_date
                existing.bidder_org_code = item.get("bidderOrgCode")
                existing.right_holder_code = item.get("rightHolderCode")
                existing.bidd_type_code = item.get("biddTypeCode")
                existing.ownership_forms_code = item.get("ownershipFormsCode")
                existing.subject_estate_code = item.get("subjectEstateCode")
                existing.subject_right_holder_code = item.get("subjectRightHolderCode")
                existing.payload = item
                existing.structure_version = structure_version
                updated += 1

        db.commit()
    finally:
        db.close()

    return inserted, updated, invalid


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.dataset_file and args.structure_file:
        return Path(args.dataset_file), Path(args.structure_file)

    meta_path = Path(args.meta_file)
    meta = load_json(meta_path)
    return Path(meta["dataset_file"]), Path(meta["structure_file"])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Импорт последнего data-*.json в БД с валидацией по structure-*.json (после alembic upgrade head)."
    )
    parser.add_argument("--dataset-file", default="")
    parser.add_argument("--structure-file", default="")
    parser.add_argument(
        "--meta-file",
        default=str(Path(__file__).resolve().parents[2] / "data" / "raw" / "latest_opendata_meta.json"),
    )
    args = parser.parse_args()

    dataset_path, structure_path = resolve_paths(args)
    inserted, updated, invalid = import_dataset(dataset_path, structure_path)

    print("Импорт завершен:")
    print(f"- dataset:   {dataset_path}")
    print(f"- structure: {structure_path}")
    print(f"- inserted:  {inserted}")
    print(f"- updated:   {updated}")
    print(f"- invalid:   {invalid}")


if __name__ == "__main__":
    main()
