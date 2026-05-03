"""
One-off migration script: Copy data from local SQLite to Supabase/Postgres.

USAGE (PowerShell):
  $env:SUPABASE_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_REAL_PASSWORD@db.nyrjcrvmgjodjywhhgyn.supabase.co:5432/postgres"
  python backend/scripts/migrate_sqlite_to_supabase.py

IMPORTANT:
- BACKUP your existing SQLite database file (marketplace.db) before migration.
- Do not commit secrets.

Safe to re-run: uses id-based merge logic; if records already exist with same PK they'll be skipped/updated.
"""
from __future__ import annotations
import os
import sqlite3
from typing import Type
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import your SQLAlchemy models
import sys
from pathlib import Path

# Ensure script can import app package when run from backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.database import Base
from migration_common import MODEL_ORDER, SQLITE_URL

POSTGRES_URL = os.environ.get("SUPABASE_DATABASE_URL")
if not POSTGRES_URL:
    raise SystemExit("Environment variable SUPABASE_DATABASE_URL is required.")

# Diagnostics: print sanitized connection info and attempt DNS resolution early
def _diagnose_connection(url: str) -> None:
    try:
        from urllib.parse import urlparse
        import socket
        parsed = urlparse(url)
        host = parsed.hostname or "(no host)"
        print(f"[DIAG] Target host: {host}")
        # Mask password
        if parsed.password:
            masked_pw = parsed.password[:2] + "***" + parsed.password[-2:]
            print(f"[DIAG] Using user: {parsed.username} password: {masked_pw}")
        # DNS resolution
        try:
            ip = socket.gethostbyname(host)
            print(f"[DIAG] DNS resolution OK: {host} -> {ip}")
        except Exception as e:
            print(f"[DIAG][WARN] DNS resolution failed for {host}: {e}")
            print("[DIAG][HINT] If this is a Windows environment without internet access or DNS blocked, verify network or try again later.")
    except Exception as e:
        print(f"[DIAG] Connection diagnostics failed: {e}")

_diagnose_connection(POSTGRES_URL)

# Engines
sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
pg_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)

SqliteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)

BATCH_SIZE = 500

def build_fk_validator(sqlite_path: Path):
    conn = sqlite3.connect(str(sqlite_path))
    cur = conn.cursor()
    fk_rules: dict[str, list[tuple[str, str, str]]] = {}
    ref_cache: dict[tuple[str, str], set[object]] = {}

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        cur.execute(f"PRAGMA foreign_key_list('{table}')")
        rules = [(row[3], row[2], row[4]) for row in cur.fetchall()]
        if rules:
            fk_rules[table] = rules
            for _, ref_table, ref_col in rules:
                key = (ref_table, ref_col)
                if key not in ref_cache:
                    cur.execute(f'SELECT "{ref_col}" FROM "{ref_table}"')
                    ref_cache[key] = {r[0] for r in cur.fetchall()}

    def validate(table: str, data: dict) -> tuple[bool, str | None]:
        for from_col, ref_table, ref_col in fk_rules.get(table, []):
            value = data.get(from_col)
            if value is None:
                continue
            if value not in ref_cache[(ref_table, ref_col)]:
                return False, f"{from_col}={value} missing {ref_table}.{ref_col}"
        return True, None

    return validate


def migrate_table(sqlite_sess, pg_sess, model: Type, validate_row) -> dict:
    """Migrate rows for a single model in batches. Returns a summary dict."""
    total = sqlite_sess.query(model).count()
    migrated = 0
    skipped = 0
    skipped_examples: list[str] = []
    offset = 0
    while True:
        rows = sqlite_sess.query(model).offset(offset).limit(BATCH_SIZE).all()
        if not rows:
            break
        with pg_sess.no_autoflush:
            for row in rows:
                data = {col.name: getattr(row, col.name) for col in model.__table__.columns}
                is_valid, reason = validate_row(model.__tablename__, data)
                if not is_valid:
                    skipped += 1
                    if len(skipped_examples) < 5:
                        skipped_examples.append(f"id={data.get('id')} {reason}")
                    continue
                obj = model(**data)
                # Use merge to handle existing PK conflicts gracefully
                pg_sess.merge(obj)
        try:
            pg_sess.commit()
        except IntegrityError as e:
            pg_sess.rollback()
            print(f"[WARN] Integrity error on commit for {model.__name__}: {e}")
        migrated += len(rows) - sum(1 for row in rows if not validate_row(model.__tablename__, {col.name: getattr(row, col.name) for col in model.__table__.columns})[0])
        offset += BATCH_SIZE
        print(f"{model.__name__}: migrated {migrated}/{total}" + (f" (skipped {skipped})" if skipped else ""))
    return {"model": model.__name__, "total": total, "migrated": migrated, "skipped": skipped, "examples": skipped_examples}

def main():
    print("== Ensuring target schema exists (create_all) ==")
    Base.metadata.create_all(bind=pg_engine)
    sqlite_sess = SqliteSession()
    pg_sess = PgSession()
    validate_row = build_fk_validator(BASE_DIR / "marketplace.db")
    summaries = []
    for model in MODEL_ORDER:
        print(f"\n== Migrating {model.__name__} ==")
        summary = migrate_table(sqlite_sess, pg_sess, model, validate_row)
        summaries.append(summary)
    print("\nMigration complete. Summary:")
    for s in summaries:
        line = f"  {s['model']}: {s['migrated']} / {s['total']}"
        if s["skipped"]:
            line += f" (skipped {s['skipped']})"
        print(line)
        for example in s["examples"]:
            print(f"    - {example}")
    with pg_engine.begin() as conn:
        for model in MODEL_ORDER:
            conn.exec_driver_sql(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{model.__tablename__}', 'id'),
                    COALESCE((SELECT MAX(id) FROM "{model.__tablename__}"), 1),
                    COALESCE((SELECT MAX(id) FROM "{model.__tablename__}"), 0) > 0
                )
                """
            )
    print("\nValidate counts in Postgres with SQL queries as needed.")
    print("REMINDER: After verifying, set USE_SUPABASE=true in .env and restart the backend.")

if __name__ == "__main__":
    main()
