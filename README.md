# Debtrix Backend (FastAPI)

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in real values
```

Generate a token encryption key (used to encrypt GitHub tokens at rest):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste the output into `TOKEN_ENCRYPTION_KEY` in `.env`.

## Run

You need Redis running locally (`redis-server`), plus two processes:

```bash
# Terminal 1 — the API
uvicorn app.main:app --reload

# Terminal 2 — the background scan worker
python -m app.workers.worker_entry
```

API available at `http://localhost:8000`. Health check: `GET /health`.

## How a scan works end-to-end

1. User connects GitHub via `GET /api/auth/github/login`
2. User picks a repo: `GET /api/repositories/available` → `POST /api/repositories/connect`
3. User triggers a scan: `POST /api/repositories/{id}/scan` → enqueues a job on Redis
4. The worker process picks it up, clones the repo, runs `radon`/`lizard` +
   git churn analysis, computes financial loss, saves metrics, then
   **deletes the clone** (zero-retention) — see `app/workers/scan_worker.py`
5. Frontend polls `GET /api/dashboard/scan/{scan_job_id}/status` until `completed`
6. Frontend fetches `GET /api/dashboard/repository/{repository_id}/latest` for
   the executive dashboard data (health score, $ loss, top 3 fixes)

## Structure

```
app/
  core/         # config, database session, security (JWT + token encryption), Redis queue
  models/       # SQLAlchemy models (mirrors schema.sql)
  api/routes/   # auth_github, repositories, dashboard
  api/deps.py   # get_current_user auth dependency
  services/     # complexity_analyzer, churn_analyzer, financial_loss (the core algorithm)
  workers/      # scan_worker (the pipeline), worker_entry (process entrypoint)
```

## Zero-retention policy

Cloned repositories live only in `CLONE_TMP_DIR` (see `.env`) for the
duration of a scan. Workers must delete this directory immediately
after extracting metrics, and must record `source_purged_at` on the
`scan_jobs` row as proof. Never commit or log raw source code.
