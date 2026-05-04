"""Dev-only helper: bring an existing SQLite schema up to current models.

In dev we rely on Base.metadata.create_all() which only creates missing tables.
When ORM models add new columns, run this script once to ALTER existing tables.
For PostgreSQL / production use Alembic migrations instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # noqa: F401  - register ORM models on Base.metadata


SQLITE_TYPE_MAP = {
    "VARCHAR": "VARCHAR",
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "FLOAT": "REAL",
    "BOOLEAN": "BOOLEAN",
    "DATETIME": "DATETIME",
    "JSON": "JSON",
}


def _column_sql(column) -> str:
    type_str = column.type.compile(dialect=engine.dialect)
    parts = [f'"{column.name}"', type_str]

    if not column.nullable:
        parts.append("NOT NULL")
    if column.server_default is not None:
        default_arg = column.server_default.arg
        default_text = default_arg.text if hasattr(default_arg, "text") else str(default_arg)
        parts.append(f"DEFAULT {default_text}")
    return " ".join(parts)


def sync() -> None:
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                sql = f'ALTER TABLE "{table.name}" ADD COLUMN {_column_sql(column)}'
                print(f"applying: {sql}")
                conn.execute(text(sql))

    print("dev schema sync complete")


if __name__ == "__main__":
    sync()
