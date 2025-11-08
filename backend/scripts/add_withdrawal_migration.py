"""
Idempotent migration script to add payout-related columns to `sellers` and
withdrawal-tracking columns to `withdrawal_requests` for SQLite databases.

Usage: python scripts/add_withdrawal_migration.py

This script uses the project's SQLAlchemy engine (imported from app.database)
so it respects the configured database URL (sqlite file path or other DB).
It only runs ALTER TABLE ADD COLUMN when the column is missing.
"""
import sys
import json
from pathlib import Path
from sqlalchemy import text

# Ensure project root is on sys.path so "app" imports succeed when running this
# script directly from the backend folder.
proj_root = Path(__file__).resolve().parents[1]
if str(proj_root) not in sys.path:
    sys.path.insert(0, str(proj_root))

try:
    from app.database import engine
except Exception as e:
    print("Failed to import database engine from app.database:", e)
    print("sys.path:", sys.path)
    sys.exit(1)

conn = engine.connect()
trans = conn.begin()
try:
    def existing_columns(table_name: str):
        # SQLite: PRAGMA table_info(table_name)
        res = conn.execute(text(f"PRAGMA table_info('{table_name}')"))
        return [row[1] for row in res.fetchall()]

    # Sellers table additions
    seller_cols = existing_columns('sellers')
    sellers_to_add = [
        ("payout_method", "TEXT"),
        ("bank_name", "TEXT"),
        ("bank_account_name", "TEXT"),
        ("bank_account_number", "TEXT"),
        ("bank_routing_number", "TEXT"),
        ("paypal_email", "TEXT"),
    ]

    for col, col_type in sellers_to_add:
        if col not in seller_cols:
            print(f"Adding column {col} to sellers")
            conn.execute(text(f"ALTER TABLE sellers ADD COLUMN {col} {col_type}"))
        else:
            print(f"Column {col} already exists on sellers, skipping")

    # Withdrawal requests additions
    wd_cols = existing_columns('withdrawal_requests')
    withdrawals_to_add = [
        ("payout_reference", "TEXT"),
        ("paid_at", "DATETIME"),
        ("payout_snapshot", "TEXT"),
    ]

    for col, col_type in withdrawals_to_add:
        if col not in wd_cols:
            print(f"Adding column {col} to withdrawal_requests")
            conn.execute(text(f"ALTER TABLE withdrawal_requests ADD COLUMN {col} {col_type}"))
        else:
            print(f"Column {col} already exists on withdrawal_requests, skipping")

    trans.commit()
    print("Migration completed successfully.")
except Exception as exc:
    print("Migration failed:", exc)
    trans.rollback()
    sys.exit(1)
finally:
    conn.close()
