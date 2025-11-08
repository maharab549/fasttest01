# Offline migration fallback & automation: SQLite  Supabase via CSV

If your development machine cannot resolve Supabase DNS or has outbound connections blocked, use this offline-friendly path to move your data.

## 1) Export CSVs from SQLite

- From the `backend` folder, run:
  - PowerShell: `python scripts/export_sqlite_to_csv.py`
- Outputs are written to `backend/migration_exports/` — one CSV per table with headers.

## 2) Prepare your Supabase schema

- Ensure your Supabase database schema matches your models (run `Base.metadata.create_all` from the backend connected to Supabase, or execute your Alembic migrations if you use them).
- Alternatively, use the Supabase SQL editor to create tables and columns that mirror your SQLAlchemy models in `app/models.py`.

## 3) Import CSVs in Supabase UI

- In Supabase, open Database → Tables → Select a table → Import data → Upload corresponding CSV.
- Map each CSV column to the matching DB column. Keep the ID/PK columns intact to preserve relationships.
- Recommended order (to respect foreign keys):
  1. User
  2. Seller
  3. Category
  4. Product
  5. ProductImage
  6. ProductVariant
  7. Order
  8. OrderItem
  9. Return
  10. ReturnItem
  11. CartItem
  12. Review
  13. Notification
  14. Message
  15. Favorite
  16. SMSMessage
  17. RewardTier
  18. LoyaltyAccount
  19. PointsTransaction
  20. Redemption
  21. WithdrawalRequest

## 4) Verify counts

- Use the Supabase SQL editor to run `SELECT COUNT(*) FROM <table>;` for each table and compare with the CSV export console output.

## 5) (Optional) Automated CSV upload

Once DNS/network access to Supabase works you can import all CSVs automatically:

1. Ensure environment variable `SUPABASE_DATABASE_URL` is set (same one the app will use).
2. Run: `python scripts/auto_import_csvs_to_supabase.py`
3. The script will:
  - Validate connectivity
  - Enumerate `migration_exports/*.csv`
  - Map file name → table name (case-insensitive)
  - Use PostgreSQL `COPY` for fast bulk load (inside a transaction per table)
  - Skip tables already containing rows unless `--force` flag is provided
4. Re-run the verification script to confirm counts (it will show Postgres counts once DNS works).

If a table has FK dependencies, order is enforced automatically using the same ordered list from the export script.

CLI help:
```
python scripts/auto_import_csvs_to_supabase.py --help
```

## 6) Switch backend to Supabase

- In your `.env`, set `USE_SUPABASE=true` and `SUPABASE_DATABASE_URL` to your connection string.
- Restart the backend. Hit the health endpoint to verify connectivity.

## Data type mapping (SQLite → Postgres quick guide)

| Model / Column (typical) | SQLite affinity | Recommended Postgres | Notes |
|--------------------------|-----------------|----------------------|-------|
| Integer PK ids           | INTEGER         | BIGINT / SERIAL / IDENTITY | Use `BIGINT` if values may grow; Supabase default is `bigint` for `id` |
| Text fields (names, etc) | TEXT            | TEXT                 | Keep as `TEXT` unless length constraints matter |
| Short codes / enums      | TEXT            | VARCHAR(n) OR TEXT + CHECK | Use ENUM type if stable list (optional) |
| Boolean flags            | INTEGER (0/1)   | BOOLEAN              | Ensure CSV has `true/false` or `1/0` (psycopg2 interprets) |
| Monetary amounts         | REAL / NUMERIC  | NUMERIC(12,2)        | Avoid float rounding issues |
| Timestamps               | TEXT / NUMERIC  | TIMESTAMPTZ          | Supabase defaults often ok; ensure UTC consistency |
| JSON payloads            | TEXT            | JSONB                | Convert only if queries on JSON content are needed |
| Foreign keys             | INTEGER         | BIGINT               | Match referenced PK type |

Null handling: For automated COPY import we force empty fields to NULL only for non-text columns to avoid type errors.

## Troubleshooting CSV import

| Issue | Symptom | Fix |
|-------|---------|-----|
| FK constraint fails | Import stops mid-table | Import parent tables first or temporarily disable constraints if allowed |
| Encoding error | ERROR: invalid byte sequence | Ensure files are UTF-8 (they are by script); re-export if modified in Excel |
| Large row fails | Field too large / truncation | Increase column type (e.g. TEXT) before import |
| Duplicate key | Primary key conflict | Truncate target table or run with `--force --truncate` (if supported by script) |
| Boolean misread | All set to false | Ensure CSV uses `true/false` or `1/0` |
| Timezone drift | Times appear shifted | Ensure app writes/reads in UTC; set `TIMEZONE='UTC'` at DB/session level |
| COPY denied | Permission error | Use the `postgres` service role string (not anon/public) |

If imports partially succeed you can `TRUNCATE TABLE <name> CASCADE;` and retry.

## Alembic baseline (after migration)

After data is in Postgres:
1. Initialize Alembic if not already (`alembic init alembic`).
2. Generate a revision autogenerate to capture current model state: `alembic revision --autogenerate -m "baseline"`.
3. Mark it as the starting point: Ensure no pending diffs; then `alembic upgrade head` (no-op if schema matches).
4. Future schema changes: modify models → `alembic revision --autogenerate -m "add_xyz"` → `alembic upgrade head`.

Document the revision ID in `IMPLEMENTATION_CHECKLIST.md` so deploy environments can sync.

## Notes

- This path avoids a live TCP connection during migration  useful when DNS or firewall rules block direct access.
- If you have very large tables, consider splitting CSV files or using the Supabase CLI/`pg_dump`/`psql` from a machine with working network access.
- Bulk imports via `COPY` bypass row-level triggers; if you later add audit triggers, re-enable them after import.
