# Database Migration: SQLite → Supabase Postgres

## Overview
This guide describes moving the existing local SQLite database (`marketplace.db`) to a managed Postgres instance on Supabase. After migration you can enable `USE_SUPABASE=true` and run the backend against Postgres.

## 1. Prerequisites
- Supabase project with Postgres connection string.
- Python dependencies installed from `requirements.txt`.
- Backup of `marketplace.db` (copy the file somewhere safe).

## 2. Environment Variables (.env)
```
# Local fallback
DATABASE_URL=sqlite:///./marketplace.db

# Supabase Postgres (replace YOUR_PASSWORD with the actual password)
SUPABASE_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@db.nyrjcrvmgjodjywhhgyn.supabase.co:5432/postgres
USE_SUPABASE=false  # flip to true after successful migration
```

## 3. Alembic (Optional but Recommended)
If you intend to version schema changes:
```
pip install alembic
alembic init alembic
# Edit alembic.ini: sqlalchemy.url = sqlite:///./marketplace.db
alembic revision --autogenerate -m "baseline"
alembic upgrade head
# Switch sqlalchemy.url in alembic.ini to SUPABASE_DATABASE_URL
alembic upgrade head
```

## 4. Migration Script
A one-off script was added: `backend/scripts/migrate_sqlite_to_supabase.py`.
Run it with the Supabase URL exported:
```
$env:SUPABASE_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@db.nyrjcrvmgjodjywhhgyn.supabase.co:5432/postgres"
python backend/scripts/migrate_sqlite_to_supabase.py
```

The script:
- Creates tables in Postgres (via `Base.metadata.create_all`) if not existing.
- Copies rows table by table in dependency order.
- Uses `merge` to avoid PK conflicts.

## 5. Verification
After script finishes:
- Compare row counts:
```
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM products;
SELECT COUNT(*) FROM orders;
```
- Spot check a few records.
- Confirm JSON fields persisted correctly.

## 6. Switch Application to Supabase
In `.env`:
```
USE_SUPABASE=true
```
Restart backend:
```
uvicorn app.main:app --reload
```
Hit health endpoint `/api/v1/admin/health/status` and verify `database.status` reports `healthy`.

## 7. Pooling
`database.py` now sets `pool_size=5` and `max_overflow=10` for Postgres to control connection usage.
Tune based on traffic & Supabase limits.

## 8. Row Level Security (RLS)
Supabase enables RLS by default. For early backend‑only access you can disable per table:
```
ALTER TABLE products DISABLE ROW LEVEL SECURITY;
```
Or define policies (example open read):
```
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_products ON products FOR SELECT USING (true);
```
If using the service role key on the backend, RLS policies may be simplified.

## 9. Common Issues
| Issue | Cause | Resolution |
|-------|------|------------|
| OperationalError: auth failed | Bad password | Re-copy connection string |
| relation does not exist | Tables not created | Run migration script / Alembic upgrade |
| IntegrityError duplicate key | Data already migrated | Accept or truncate target table before re-run |
| Slow queries | Missing indexes | Add indexes in Alembic migration |
| JSON casting errors | Schema mismatch | Ensure JSON columns use `JSON` type |

## 10. Rollback Strategy
If Postgres issues arise:
1. Set `USE_SUPABASE=false` in `.env`.
2. Restart backend (falls back to SQLite).
3. Fix root cause (credentials/network/schema).
4. Re-enable Supabase after resolution.

## 11. Next Improvements
- Introduce Alembic migrations for future schema changes.
- Add `GIN` indexes for JSON/text search fields.
- Implement materialized views for analytics.
- Add automated nightly backup snapshot using Supabase infrastructure.

---
Migration complete. Validate thoroughly before removing the SQLite file.
