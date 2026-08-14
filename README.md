# EmergencyIQ

EmergencyIQ: AI-Powered Emergency Call Prioritization and Smart Dispatch Management Platform

This repository contains two folders: `frontend` (React + Vite) and `backend` (FastAPI).

Quick setup commands

Frontend (from repo root):

```bash
cd frontend
# If you haven't installed node_modules yet
npm install
# Run dev server
npm run dev
```

Backend (from repo root):

```bash
cd backend
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
# or Command Prompt
.\.venv\Scripts\activate.bat
pip install -r requirements.txt
# Run the server
uvicorn main:app --reload --port 8000
```

Notes
- This is a skeleton project. No business logic implemented yet.
- Frontend uses Vite + React + MUI. Backend uses FastAPI.
