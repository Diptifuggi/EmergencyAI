# EmergencyIQ — Backend

Lightweight FastAPI backend for EmergencyIQ tailored for low-spec development machines (Intel i3, ~8GB RAM). This guide explains local setup and running the service on Windows.

Requirements
- Python 3.11
- PostgreSQL 16 with pgvector extension (optional for later features)

Setup (Windows)

1. Create a virtual environment and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Create a .env file based on `.env.example` and set `DATABASE_URL` to your local Postgres instance.

4. Run Alembic migrations (ensure alembic is configured and `alembic/` is present):

```powershell
alembic upgrade head
```

5. Start the app with Uvicorn (reload enabled for development):

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Notes for low-spec machines
- Avoid running heavy background processes while developing (e.g., large model servers).
- Keep database tuned for local usage (lower memory settings) and avoid heavy concurrent load.
- No Docker required; the project runs natively on Windows using a venv.
