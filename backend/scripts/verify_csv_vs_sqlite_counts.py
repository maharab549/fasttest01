"""Compare row counts between current SQLite DB and exported CSVs.

Use this after running export_sqlite_to_csv.py to ensure CSVs match the source DB.
If Supabase is reachable and SUPABASE_DATABASE_URL is set, also fetch counts from Postgres.

Usage (PowerShell):
  cd backend
  python scripts/verify_csv_vs_sqlite_counts.py
"""
from __future__ import annotations
import csv
import os
from pathlib import Path
from typing import Sequence, Type, Dict
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.models import (
    User, Seller, Category, Product, ProductVariant, ProductImage, Order, OrderItem,
    Return, ReturnItem, CartItem, Review, Notification, Message, Favorite,
    SMSMessage, RewardTier, LoyaltyAccount, PointsTransaction, Redemption,
    WithdrawalRequest
)

MODEL_ORDER: Sequence[Type] = [
    User,
    Seller,
    Category,
    Product,
    ProductImage,
    ProductVariant,
    Order,
    OrderItem,
    Return,
    ReturnItem,
    CartItem,
    Review,
    Notification,
    Message,
    Favorite,
    SMSMessage,
    RewardTier,
    LoyaltyAccount,
    PointsTransaction,
    Redemption,
    WithdrawalRequest,
]

SQLITE_URL = "sqlite:///./marketplace.db"
EXPORT_DIR = BASE_DIR / "migration_exports"
POSTGRES_URL = os.environ.get("SUPABASE_DATABASE_URL")

# Increase field size limit for large text fields in CSVs
try:
    import sys as _sys
    csv.field_size_limit(_sys.maxsize)
except Exception:
    # Fallback to a large fixed limit
    csv.field_size_limit(10_000_000)


def load_csv_count(model_name: str) -> int | None:
    path = EXPORT_DIR / f"{model_name}.csv"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)  # header
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def main() -> None:
    if not EXPORT_DIR.exists():
        print(f"[ERROR] Export directory {EXPORT_DIR} not found. Run export_sqlite_to_csv.py first.")
        return

    engine_sqlite = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine_sqlite)
    sess = Session()

    pg_engine = None
    if POSTGRES_URL:
        try:
            pg_engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[INFO] Connected to Postgres for count comparison.")
        except Exception as e:
            print(f"[WARN] Could not connect to Postgres: {e}")
            pg_engine = None
    else:
        print("[INFO] SUPABASE_DATABASE_URL not set; skipping Postgres comparison.")

    summary: Dict[str, Dict[str, int | None]] = {}

    for model in MODEL_ORDER:
        name = model.__name__
        sqlite_count = sess.query(model).count()
        csv_count = load_csv_count(name)
        pg_count = None
        if pg_engine is not None:
            try:
                with pg_engine.connect() as conn:
                    result = conn.execute(text(f'SELECT COUNT(*) FROM "{model.__tablename__}"'))
                    pg_count = result.scalar_one()
            except Exception as e:
                print(f"[WARN] Postgres count failed for {name}: {e}")
        summary[name] = {"sqlite": sqlite_count, "csv": csv_count, "postgres": pg_count}

    # Report
    print("\nRow Count Comparison (sqlite vs csv vs postgres):")
    mismatches = 0
    for name, counts in summary.items():
        sqlite_c = counts["sqlite"]
        csv_c = counts["csv"]
        pg_c = counts["postgres"]
        flag = ""
        if csv_c is not None and csv_c != sqlite_c:
            flag = " <== CSV MISMATCH"
            mismatches += 1
        elif pg_c is not None and pg_c != sqlite_c:
            flag = " <== POSTGRES MISMATCH"
            mismatches += 1
        print(f"{name:20} sqlite={sqlite_c:5} csv={str(csv_c):5} postgres={str(pg_c):5}{flag}")

    if mismatches == 0:
        print("\nAll counts match for available sources.")
    else:
        print(f"\n{mismatches} table(s) have mismatched counts. Investigate before switching.")


if __name__ == "__main__":
    main()
