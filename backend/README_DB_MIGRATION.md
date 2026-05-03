# Supabase Migration Notes

## Source Of Truth

Use `backend/marketplace.db` as the source database.

Do not use the root-level `db_cluster-26-11-2025@14-14-31.backup` as the primary import source.
It is an older PostgreSQL cluster dump and its row counts are far smaller than the live SQLite database.

Current SQLite database summary:

- `24` tables
- `466` products
- `27` orders
- `14` users
- `47` messages
- `221` notifications
- `5` banners

## Preferred Path

From the `backend` folder:

```powershell
$env:SUPABASE_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
python scripts/migrate_sqlite_to_supabase.py
```

What this does:

- creates the Postgres schema from the SQLAlchemy models
- copies data from `marketplace.db`
- preserves primary keys
- resets Postgres sequences after import

## Manual CSV Fallback

If you want a dashboard-driven import path instead:

```powershell
python scripts/export_sqlite_to_csv.py
python scripts/verify_csv_vs_sqlite_counts.py
```

Then import with:

```powershell
$env:SUPABASE_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
python scripts/auto_import_csvs_to_supabase.py
```

## Switch The Backend To Supabase

Update `.env` after the data is verified in Supabase:

```env
DATABASE_URL=sqlite:///./marketplace.db
SUPABASE_DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
USE_SUPABASE=true
```

Then restart the backend.

## Quick Verification SQL

Run these in Supabase SQL editor after import:

```sql
select count(*) from users;
select count(*) from products;
select count(*) from orders;
select count(*) from messages;
select count(*) from notifications;
select count(*) from banners;
```
