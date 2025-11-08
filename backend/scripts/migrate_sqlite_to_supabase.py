"""
One-off migration script: Copy data from local SQLite to Supabase/Postgres.

USAGE (PowerShell):
  $env:SUPABASE_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_REAL_PASSWORD@db.nyrjcrvmgjodjywhhgyn.supabase.co:5432/postgres"
  python backend/scripts/migrate_sqlite_to_supabase.py

IMPORTANT:
- Ensure you have run Alembic (or Base.metadata.create_all on Postgres) BEFORE running this.
- BACKUP your existing SQLite database file (marketplace.db) before migration.
- Do not commit secrets.

Safe to re-run: uses id-based merge logic; if records already exist with same PK they'll be skipped/updated.
"""
from __future__ import annotations
import os
from typing import Sequence, Type
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import your SQLAlchemy models
import sys
from pathlib import Path

# Ensure script can import app package when run from backend directory
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / 'app'
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.models import (
    User, Seller, Category, Product, ProductVariant, ProductImage, Order, OrderItem,
    Return, ReturnItem, CartItem, Review, Notification, Message, Favorite,
    SMSMessage, RewardTier, LoyaltyAccount, PointsTransaction, Redemption,
    WithdrawalRequest
)
from app.database import Base

SQLITE_URL = "sqlite:///./marketplace.db"
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

# Ordered models (respect FK dependencies: users before sellers, products before variants, etc.)
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

BATCH_SIZE = 500

def migrate_table(sqlite_sess, pg_sess, model: Type) -> dict:
    """Migrate rows for a single model in batches. Returns a summary dict."""
    total = sqlite_sess.query(model).count()
    migrated = 0
    offset = 0
    while True:
        rows = sqlite_sess.query(model).offset(offset).limit(BATCH_SIZE).all()
        if not rows:
            break
        for row in rows:
            # Build column dict
            data = {col.name: getattr(row, col.name) for col in model.__table__.columns}
            obj = model(**data)
            # Use merge to handle existing PK conflicts gracefully
            pg_sess.merge(obj)
        try:
            pg_sess.commit()
        except IntegrityError as e:
            pg_sess.rollback()
            print(f"[WARN] Integrity error on commit for {model.__name__}: {e}")
        migrated += len(rows)
        offset += BATCH_SIZE
        print(f"{model.__name__}: migrated {migrated}/{total}")
    return {"model": model.__name__, "total": total, "migrated": migrated}

def main():
    print("== Ensuring target schema exists (create_all) ==")
    Base.metadata.create_all(bind=pg_engine)
    sqlite_sess = SqliteSession()
    pg_sess = PgSession()
    summaries = []
    for model in MODEL_ORDER:
        print(f"\n== Migrating {model.__name__} ==")
        summary = migrate_table(sqlite_sess, pg_sess, model)
        summaries.append(summary)
    print("\nMigration complete. Summary:")
    for s in summaries:
        print(f"  {s['model']}: {s['migrated']} / {s['total']}")
    print("\nValidate counts in Postgres with SQL queries as needed.")
    print("REMINDER: After verifying, set USE_SUPABASE=true in .env and restart the backend.")

if __name__ == "__main__":
    main()
