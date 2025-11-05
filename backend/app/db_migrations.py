from __future__ import annotations

from typing import Iterable
from sqlalchemy.engine import Engine


def _get_sqlite_columns(engine: Engine, table: str) -> list[str]:
    """Return list of column names for a SQLite table."""
    with engine.connect() as conn:
        res = conn.exec_driver_sql(f"PRAGMA table_info({table})")
        rows = res.fetchall()
    # PRAGMA table_info columns: cid, name, type, notnull, dflt_value, pk
    return [row[1] for row in rows]


def _sqlite_add_column(engine: Engine, table: str, column: str, type_sql: str) -> None:
    """Add a column to a SQLite table if it does not already exist."""
    cols = set(_get_sqlite_columns(engine, table))
    if column in cols:
        return
    with engine.connect() as conn:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {type_sql}")


def ensure_message_attachment_columns(engine: Engine) -> None:
    """Ensure attachment-related columns exist on messages table.

    This provides a lightweight, Alembic-free migration for SQLite dev DBs.
    """
    # SQLite types: TEXT, INTEGER
    _sqlite_add_column(engine, "messages", "attachment_type", "TEXT")
    _sqlite_add_column(engine, "messages", "attachment_url", "TEXT")
    _sqlite_add_column(engine, "messages", "attachment_filename", "TEXT")
    _sqlite_add_column(engine, "messages", "attachment_size", "INTEGER")
    _sqlite_add_column(engine, "messages", "attachment_thumbnail", "TEXT")


def coalesce_products_null_counts(engine: Engine) -> None:
    """Backfill NULL counters to 0 to satisfy response schemas."""
    with engine.connect() as conn:
        # view_count and review_count should never be NULL
        conn.exec_driver_sql("UPDATE products SET view_count = 0 WHERE view_count IS NULL")
        conn.exec_driver_sql("UPDATE products SET review_count = 0 WHERE review_count IS NULL")


def ensure_reviews_order_id_column(engine: Engine) -> None:
    """Ensure reviews.order_id column exists (nullable INTEGER).

    Older dev SQLite DBs may miss this column; models and APIs reference it.
    """
    _sqlite_add_column(engine, "reviews", "order_id", "INTEGER")


def coalesce_orders_null_status(engine: Engine) -> None:
    """Backfill NULL/empty order.status to 'pending' to ensure UI shows a value."""
    with engine.connect() as conn:
        try:
            conn.exec_driver_sql("UPDATE orders SET status = 'pending' WHERE status IS NULL OR TRIM(status) = ''")
        except Exception:
            # best-effort
            pass


def run_all(engine: Engine) -> None:
    """Run all lightweight startup migrations idempotently."""
    try:
        ensure_message_attachment_columns(engine)
    except Exception:
        # Best-effort; don't block app startup in dev
        pass
    try:
        coalesce_products_null_counts(engine)
    except Exception:
        pass
    try:
        ensure_reviews_order_id_column(engine)
    except Exception:
        pass
    try:
        coalesce_orders_null_status(engine)
    except Exception:
        pass
