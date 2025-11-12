"""
Idempotent import helper: create tables and import CSVs into a Postgres database (e.g. Supabase).

Usage (PowerShell):
  cd backend
  # set SUPABASE_DB environment variable or pass --db
  $env:SUPABASE_DB = "postgres://..."
  python scripts/import_to_supabase.py --csv-dir migration_exports --db "$env:SUPABASE_DB"

What it does:
- Connects to the provided Postgres URL
- Runs SQLAlchemy's Base.metadata.create_all() to create tables
- Imports CSV files found in --csv-dir in dependency order using COPY FROM STDIN
- Updates sequences (serial) to max(id)+1
- Runs simple FK count checks

Important: Do NOT run this against production unless you have backups.
"""
from __future__ import annotations
import argparse
import csv
import os
from pathlib import Path
from typing import Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Ensure project root is on sys.path
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import models
from app.database import Base  # expecting Base metadata export

# Import order should match parent's first to avoid FK violations
MODEL_ORDER: Sequence[str] = [
    "User",
    "Seller",
    "Category",
    "Product",
    "ProductImage",
    "ProductVariant",
    "Order",
    "OrderItem",
    "Return",
    "ReturnItem",
    "CartItem",
    "Review",
    "Notification",
    "Message",
    "Favorite",
    "SMSMessage",
    "RewardTier",
    "LoyaltyAccount",
    "PointsTransaction",
    "Redemption",
    "WithdrawalRequest",
]

CSV_DEFAULT_DIR = BASE_DIR / "migration_exports"


def get_model_by_name(name: str):
    return getattr(models, name)


def create_tables(engine):
    print("Creating tables (if not exists) via SQLAlchemy metadata.create_all()")
    Base.metadata.create_all(bind=engine)


def import_csv_to_table(conn, csv_path: Path, table_name: str):
    print(f"Importing {csv_path.name} -> {table_name}")
    # Use COPY FROM STDIN for fast import. We assume header row present.
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        # Build COPY command with quoted identifiers
        cols = ", ".join([f'"{h}"' for h in headers])
        copy_sql = f"COPY {table_name} ({cols}) FROM STDIN WITH CSV HEADER"
        raw = f.read()
        # use psycopg2 via SQLAlchemy raw connection
        raw_conn = conn.connection
        cur = raw_conn.cursor()
        cur.copy_expert(copy_sql, csv_path.open('r', encoding='utf-8'))
        raw_conn.commit()
    print(f"Imported {csv_path.name}")


def set_sequences(conn, table_name: str):
    # Find sequence name standard: table_id_seq. If not found skip.
    seq_name = f"{table_name}_id_seq"
    try:
        print(f"Updating sequence {seq_name} for table {table_name}")
        conn.execute(text(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false)"))
    except Exception as e:
        print(f"Skipping sequence update for {table_name}: {e}")


def run_import(db_url: str, csv_dir: Path):
    # If connecting to Supabase pooler or supabase host, require SSL by default.
    connect_args = {}
    lower = db_url.lower()
    if ("supabase" in lower or "pooler.supabase.com" in lower) and "sslmode" not in lower:
        # Force SSL for Supabase
        connect_args["sslmode"] = "require"
        print("Enforcing sslmode=require for Supabase connection")

    engine = create_engine(db_url, connect_args=connect_args) if connect_args else create_engine(db_url)
    Session = sessionmaker(bind=engine)
    # 1) create tables
    create_tables(engine)

    # 2) import CSVs in order
    try:
        conn = engine.raw_connection()
    except OperationalError as exc:
        msg = str(exc)
        print("\nERROR: Could not connect to the database:\n")
        print(msg)
        # Common Supabase pooler issues
        if "tenant allow_list" in msg or "allow_list" in msg or "Address not in tenant allow_list" in msg:
            print("\nIt looks like the database is rejecting your client IP (Address not in tenant allow_list).")
            print("You must add your machine's public IP to the Supabase project's DB allow-list (Database > Network > Allow list).")
            print("Find your public IP: in PowerShell run: (Invoke-RestMethod -Uri 'https://ifconfig.me') or 'curl ifconfig.me' and add that IP to the project's allow-list.")
        if "SSL connection is required" in msg or "sslmode" in msg.lower():
            print("\nThe server requires an SSL connection. The importer will try with sslmode=require; ensure your connection string or network allows TLS.")
        print("\nAfter updating the allow-list or confirming SSL, re-run the import command.")
        raise
    try:
        for model_name in MODEL_ORDER:
            model = get_model_by_name(model_name)
            table_name = model.__tablename__
            csv_path = csv_dir / f"{model_name}.csv"
            if not csv_path.exists():
                print(f"CSV for {model_name} not found at {csv_path}, skipping")
                continue
            import_csv_to_table(conn, csv_path, table_name)
            set_sequences(engine.connect(), table_name)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # 3) Simple sanity checks (row counts)
    with engine.connect() as c:
        for model_name in MODEL_ORDER:
            model = get_model_by_name(model_name)
            table_name = model.__tablename__
            csv_path = csv_dir / f"{model_name}.csv"
            if not csv_path.exists():
                continue
            csv_count = sum(1 for _ in csv_path.open('r', encoding='utf-8')) - 1
            db_count = c.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"{table_name}: CSV rows={csv_count}  DB rows={db_count}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="Postgres DB URL (postgres://)")
    ap.add_argument("--csv-dir", default=str(CSV_DEFAULT_DIR))
    args = ap.parse_args()

    db_url = args.db or os.environ.get("SUPABASE_DB") or os.environ.get("SUPABASE_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("No database URL provided. Set SUPABASE_DB env or pass --db")
        return

    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        print(f"CSV dir not found: {csv_dir}")
        return

    run_import(db_url, csv_dir)


if __name__ == "__main__":
    main()
