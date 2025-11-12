Import helper — overview

This folder contains a helper to import the CSV exports into a Postgres database (Supabase).

Files
- import_to_supabase.py — idempotent importer. It will:
  - create tables via SQLAlchemy Base.metadata.create_all()
  - import CSV files from migration_exports using COPY
  - update sequences
  - run simple row-count checks

Quick usage (PowerShell):

```powershell
cd backend
$env:SUPABASE_DB = "postgres://<user>:<pw>@<host>:5432/<db>"
python .\scripts\import_to_supabase.py --csv-dir migration_exports --db $env:SUPABASE_DB
```

Notes & warnings
- Run this only against a development or staging Supabase database. Back up existing data first.
- The script assumes the CSV header names match PostgreSQL column names.
- If your CSVs contain JSON columns (textified JSON), ensure the target Postgres columns are JSONB or transform them prior to import.
- If your Supabase project uses additional schemas, update the script to prefix table names accordingly.

If you want me to run the import for you, provide the SUPABASE_DB (postgres URL). Do not paste secrets unless you want me to execute; otherwise run the command above locally and paste any errors if you want me to debug them.
 
Security note:
- Do not commit your real `.env` or credentials to git. Use `.env` locally and keep a `.env.example` (provided) in the repository with placeholders only.
- Ensure `.gitignore` includes `.env` (this repo contains a `.gitignore` with that entry).