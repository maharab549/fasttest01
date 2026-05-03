from __future__ import annotations

import json
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Sequence, Type

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import models as app_models  # noqa: F401
from app.database import Base

SQLITE_URL = "sqlite:///./marketplace.db"
EXPORT_DIR = BASE_DIR / "migration_exports"
NULL_SENTINEL = r"\N"

_MODEL_BY_TABLE = {
    mapper.local_table.name: mapper.class_
    for mapper in Base.registry.mappers
}

MODEL_ORDER: Sequence[Type[Any]] = tuple(
    _MODEL_BY_TABLE[table.name]
    for table in Base.metadata.sorted_tables
    if table.name in _MODEL_BY_TABLE
)


def normalize_postgres_url(url: str) -> str:
    return url.replace("postgresql+psycopg2://", "postgresql://", 1)


def serialize_csv_value(value: Any) -> str:
    if value is None:
        return NULL_SENTINEL
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def reset_identity_sequence(cursor: Any, table: str, pk_column: str = "id") -> None:
    cursor.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence(%s, %s),
            COALESCE((SELECT MAX("{pk_column}") FROM "{table}"), 1),
            COALESCE((SELECT MAX("{pk_column}") FROM "{table}"), 0) > 0
        )
        """,
        (table, pk_column),
    )
