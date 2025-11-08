"""
Export all SQLite tables (defined in app.models) to CSV files for manual import into Supabase Postgres.

Output directory: ../migration_exports

USAGE (PowerShell):
  cd backend
  python scripts/export_sqlite_to_csv.py

Then, in the Supabase UI, create tables (or run Base.metadata.create_all via the backend connected to Supabase),
and import each CSV into the corresponding table.
"""
from __future__ import annotations
import csv
from pathlib import Path
from typing import Sequence, Type

from sqlalchemy import create_engine
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

SQLITE_URL = "sqlite:///./marketplace.db"
EXPORT_DIR = BASE_DIR / "migration_exports"
EXPORT_DIR.mkdir(exist_ok=True)

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

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


def export_model(sess, model: Type) -> Path:
    rows = sess.query(model).all()
    cols = [c.name for c in model.__table__.columns]
    out_path = EXPORT_DIR / f"{model.__name__}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in rows:
            writer.writerow([getattr(row, c) for c in cols])
    print(f"Exported {model.__name__}: {len(rows)} rows -> {out_path.relative_to(BASE_DIR)}")
    return out_path


def main() -> None:
    print(f"Export directory: {EXPORT_DIR}")
    sess = Session()
    for model in MODEL_ORDER:
        export_model(sess, model)
    print("\nDone. Use Supabase table import to load these CSVs. Ensure column types match your models.")


if __name__ == "__main__":
    main()
