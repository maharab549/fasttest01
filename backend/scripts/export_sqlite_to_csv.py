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
from typing import Type

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from migration_common import EXPORT_DIR, MODEL_ORDER, SQLITE_URL, serialize_csv_value

EXPORT_DIR.mkdir(exist_ok=True)
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


def export_model(sess, model: Type) -> Path:
    rows = sess.query(model).all()
    cols = [c.name for c in model.__table__.columns]
    out_path = EXPORT_DIR / f"{model.__name__}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for row in rows:
            writer.writerow([serialize_csv_value(getattr(row, c)) for c in cols])
    print(f"Exported {model.__name__}: {len(rows)} rows -> {out_path.relative_to(EXPORT_DIR.parent)}")
    return out_path


def main() -> None:
    print(f"Export directory: {EXPORT_DIR}")
    sess = Session()
    for model in MODEL_ORDER:
        export_model(sess, model)
    print("\nDone. Use Supabase table import to load these CSVs. Ensure column types match your models.")


if __name__ == "__main__":
    main()
