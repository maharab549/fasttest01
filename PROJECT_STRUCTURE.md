# Project structure & deployment quick-reference

This file documents a recommended, concrete file layout for the frontend and backend in this repository, where to put the backend API URL, and a short troubleshooting checklist (DB + port) with commands you can run locally or inside the service container.

---

## Frontend (recommended)

Root: `front/frontend/`

- `.env` — local development environment variables (NOT committed for secrets). Example:
  - `VITE_API_BASE_URL=http://localhost:8000/api/v1`
  - `VITE_DEV_PROXY=0`
- `env.example` — example env values to share with the team
- `netlify.toml` — Netlify build and environment overrides (you already have one)
- `package.json`, lockfile(s)
- `vite.config.js`
- `public/` — static files served directly (index.html, images, icons)
- `src/`
  - `main.jsx` — app entry
  - `App.jsx` — top-level component and router
  - `index.css`, global styles
  - `components/` — shared UI components
  - `pages/` — route views
  - `contexts/` — React contexts (Auth, Cart, etc.)
  - `hooks/` — custom hooks
  - `lib/` — utilities and the API client
    - `api.js` — axios instance that reads `import.meta.env.VITE_API_BASE_URL`
    - `api_fixed.js` — alternate api client (if present)
  - `assets/` — images/fonts

Notes:
- Where to put backend link: set `VITE_API_BASE_URL` (either in local `.env` for dev or in your host CI/env settings for production). The frontend code uses `import.meta.env.VITE_API_BASE_URL`.
- Example production value (Netlify / deployed):
  - `VITE_API_BASE_URL=https://marketplace-backend-n2hk.onrender.com/api/v1`
- For dev CORS avoidance: set `VITE_DEV_PROXY=1` and configure `vite.config.js` proxy to forward `/api` to the backend host. Then set `VITE_API_BASE_URL=/api/v1` locally.

---

## Backend (recommended)

Root: `backend/` (in this repo under `fasttest01/backend`)

- `.env` — local env variables (do not commit secrets). Keys used in this project:
  - `database_url` or `DATABASE_URL` — fallback is SQLite by default in `config.py` (`sqlite:///./marketplace.db`).
  - `SUPABASE_DATABASE_URL` (or `supabase_database_url`) — optional Postgres/Supabase URL.
  - `USE_SUPABASE` (or `use_supabase`) — set `true` to make the app use Supabase/PG instead of sqlite.
  - `redis_url` — redis connection string if used
  - `PORT` — port uvicorn will bind to (default in code: `PORT` env, fallback `8000`)
- `requirements.txt` or `pyproject.toml`
- `Dockerfile` and `start.sh` (container entrypoint)
- `app/` — python package
  - `main.py` — FastAPI app (uvicorn run), route registration, middleware
  - `config.py` — pydantic settings (reads `.env`)
  - `database.py` — SQLAlchemy engine + session creation (uses `database_url` or `supabase_database_url`)
  - `models.py`, `schemas.py`
  - `routers/` — grouped routers (auth, products, orders, etc.)
  - `services/` — external integrations (stripe, sms, ai, etc.)
  - `ws_redis.py`, `ws_manager.py` — websockets and redis bridge
  - `db_migrations.py` or `migrations/` — migration runner
- `uploads/` — uploaded user files (ignored in git)

Important backend env guidance:
- Use consistent env names for clarity: prefer `DATABASE_URL` for Postgres, and `SUPABASE_DATABASE_URL` for Supabase role keys if required by scripts.
- If you use a managed Postgres (Supabase), the connection string often requires `?sslmode=require` or similar — include that when connecting from remote hosts.
- The app reads `PORT` and defaults to 8000. Many PaaS platforms expect the app to listen on port **8080**; set `PORT=8080` in that platform's environment variables if the platform proxy expects 8080.

---

## Netlify (frontend) specific

If you deploy the frontend on Netlify, you can set `VITE_API_BASE_URL` in `netlify.toml` under production context or via the Netlify UI env settings. Example (valid TOML):

```toml
[context.production.environment]
  VITE_API_BASE_URL = "https://marketplace-backend-n2hk.onrender.com/api/v1"
```

You already have `netlify.toml` in the repo; make sure the file uses valid TOML assignments (`key = "value"`).

---

## Quick troubleshooting checklist (DB + port)

1. Verify environment variables inside the running service (Leapcell/container):

```bash
# list DB and port related envs
env | grep -iE 'PORT|DATABASE|SUPABASE|USE_SUPABASE|REDIS|PG' || true
```

2. Check which DB URL the app will use (Python quick check):

```bash
python - <<'PY'
import os
print('DATABASE_URL:', os.environ.get('DATABASE_URL') or os.environ.get('database_url'))
print('SUPABASE_DATABASE_URL:', os.environ.get('SUPABASE_DATABASE_URL') or os.environ.get('supabase_database_url'))
print('USE_SUPABASE:', os.environ.get('USE_SUPABASE') or os.environ.get('use_supabase'))
print('PORT:', os.environ.get('PORT'))
PY
```

3. Test Postgres connection from inside the container (if using Postgres):

```bash
python - <<'PY'
import os,sys,traceback
try:
    url = os.environ.get('SUPABASE_DATABASE_URL') or os.environ.get('DATABASE_URL') or os.environ.get('database_url')
    print('Attempting DB URL:', url)
    import psycopg2
    conn = psycopg2.connect(url)
    print('DB connect OK')
    conn.close()
except Exception:
    traceback.print_exc()
    sys.exit(1)
PY
```

Common fixes:
- If psql/psycopg2 reports `Connection refused` → host/port wrong or DB not running.
- If `password authentication failed` → wrong username/password.
- If `SSL required` → add `?sslmode=require` or appropriate SSL params to the connection string.

4. Ensure `PORT` is set to the value expected by the platform (Leapcell expects 8080 in your logs). Set it before starting the app.

```bash
# Example to run locally with port 8080
export PORT=8080
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

On Windows PowerShell use `$env:PORT = 8080` before starting.

---

## Helpful commands (copy-paste)

- Create frontend `.env` with production API URL (local dev copy):

```bash
# Linux/macOS
cat > front/frontend/.env <<'EOF'
VITE_API_BASE_URL=https://marketplace-backend-n2hk.onrender.com/api/v1
VITE_DEV_PROXY=0
EOF

# PowerShell (Windows)
"VITE_API_BASE_URL=https://marketplace-backend-n2hk.onrender.com/api/v1`nVITE_DEV_PROXY=0" | Out-File -FilePath .\front\frontend\.env -Encoding utf8
```

- Locally run backend and bind to port 8080 (PowerShell):

```powershell
$env:PORT = 8080
python -m uvicorn app.main:app --host 0.0.0.0 --port $env:PORT
```

- Check frontend calls in browser devtools: open Network tab, filter by `/api/` and verify requests go to `fasttest01-maharab...apn.leapcell.dev`.

---

If you want, I can:
- Add this file to the repo (I just created it at the repo root as `PROJECT_STRUCTURE.md`).
- Create a `.env.example` or update `netlify.toml` (done) or update `front/frontend/.env` for you.

Tell me what you'd like next.