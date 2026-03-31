from __future__ import annotations

import threading

from fastapi import APIRouter
from pydantic import BaseModel

from api.deps import get_db

router = APIRouter()

# Shared state for active run
_active_run: dict | None = None
_run_lock = threading.Lock()
_stop_event = threading.Event()
_progress: dict = {"step": "", "jobs_found": 0, "jobs_new": 0, "jobs_passed": 0}


class RunRequest(BaseModel):
    dry_run: bool = False
    skip_enrichment: bool = False


def _execute_pipeline(run_request: RunRequest) -> None:
    global _active_run
    _stop_event.clear()
    _progress.update({"step": "starting", "jobs_found": 0, "jobs_new": 0, "jobs_passed": 0})
    try:
        from navy.main import run_pipeline

        run_pipeline(
            dry_run=run_request.dry_run,
            skip_enrichment=run_request.skip_enrichment,
            stop_event=_stop_event,
            progress=_progress,
        )
    except Exception:
        pass
    finally:
        with _run_lock:
            _active_run = None


@router.get("/runs")
def list_runs(page: int = 1, per_page: int = 20):
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        offset = (page - 1) * per_page
        rows = db.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ).fetchall()

        return {
            "runs": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    finally:
        db.close()


@router.get("/runs/active")
def get_active_run():
    with _run_lock:
        if _active_run:
            return {"active": True, **_active_run, "progress": dict(_progress)}
    return {"active": False}


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    db = get_db()
    try:
        row = db.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return {"error": "Run not found"}
        return dict(row)
    finally:
        db.close()


@router.post("/runs")
def trigger_run(request: RunRequest):
    global _active_run

    with _run_lock:
        if _active_run and _active_run["status"] == "running":
            return {"error": "A run is already in progress", "active_run": _active_run}
        _active_run = {
            "status": "running",
            "dry_run": request.dry_run,
            "skip_enrichment": request.skip_enrichment,
        }

    thread = threading.Thread(target=_execute_pipeline, args=(request,), daemon=True)
    thread.start()

    return {"message": "Pipeline run started", "active_run": _active_run}


@router.post("/runs/stop")
def stop_run():
    with _run_lock:
        if not _active_run or _active_run["status"] not in ("running", "stopping"):
            return {"error": "No active run to stop"}
        _stop_event.set()
        _active_run["status"] = "stopping"

    return {"message": "Stop signal sent"}
