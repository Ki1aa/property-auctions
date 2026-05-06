"""Dev-only helper: bring an existing SQLite schema up to current models.

In dev we rely on Base.metadata.create_all() which only creates missing tables.
When ORM models add new columns, run this script once to ALTER existing tables.
The script also creates missing indexes. SQLite cannot add foreign keys to an
existing table without rebuilding it, so missing FKs are reported as warnings.
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

        inspector = inspect(conn)
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue

            existing_indexes = {idx["name"] for idx in inspector.get_indexes(table.name)}
            for index in table.indexes:
                if index.name in existing_indexes:
                    continue
                print(f"creating index: {index.name}")
                index.create(bind=conn, checkfirst=True)

            existing_fks = {
                (
                    tuple(fk.get("constrained_columns") or []),
                    fk.get("referred_table"),
                    tuple(fk.get("referred_columns") or []),
                )
                for fk in inspector.get_foreign_keys(table.name)
            }
            for fk in table.foreign_key_constraints:
                expected = (
                    tuple(column.name for column in fk.columns),
                    fk.referred_table.name,
                    tuple(element.column.name for element in fk.elements),
                )
                if expected not in existing_fks:
                    print(
                        "warning: missing foreign key on existing SQLite table "
                        f"{table.name}({', '.join(expected[0])}) -> "
                        f"{expected[1]}({', '.join(expected[2])}); "
                        "SQLite requires table rebuild or fresh DB/Alembic migration."
                    )

    print("dev schema sync complete")


if __name__ == "__main__":
    sync()
