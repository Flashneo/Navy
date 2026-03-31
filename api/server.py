from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

# Ensure the project root is on sys.path (needed for Railway deployment)
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import config as config_routes
from api.routes import export as export_routes
from api.routes import jobs as job_routes
from api.routes import runs as run_routes

load_dotenv()

app = FastAPI(title="Navy — AI Job Search Agent", version="0.1.0")

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# Shared state for tracking active pipeline run
active_run: dict | None = None
active_run_lock = threading.Lock()


@app.on_event("startup")
def startup_telegram_bot():
    try:
        from navy.output.telegram import start_bot
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        start_bot(token)
    except ImportError as e:
        import logging
        logging.warning(f"Telegram bot not started: {e}")

app.include_router(job_routes.router, prefix="/api")
app.include_router(run_routes.router, prefix="/api")
app.include_router(config_routes.router, prefix="/api")
app.include_router(export_routes.router, prefix="/api")


@app.get("/api/stats")
def get_stats():
    from api.deps import get_db

    db = get_db()
    try:
        total_jobs = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        avg_score = db.execute(
            "SELECT COALESCE(AVG(relevance_score), 0) FROM jobs"
        ).fetchone()[0]
        total_runs = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]

        last_run = db.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        new_this_week = db.execute(
            "SELECT COUNT(*) FROM jobs WHERE first_seen_at >= datetime('now', '-7 days')"
        ).fetchone()[0]

        top_companies = db.execute(
            """SELECT company_name, COUNT(*) as count
            FROM jobs GROUP BY company_name
            ORDER BY count DESC LIMIT 5"""
        ).fetchall()

        return {
            "total_jobs": total_jobs,
            "new_this_week": new_this_week,
            "avg_score": round(avg_score, 2),
            "total_runs": total_runs,
            "last_run": dict(last_run) if last_run else None,
            "top_companies": [
                {"name": r["company_name"], "count": r["count"]} for r in top_companies
            ],
        }
    finally:
        db.close()
