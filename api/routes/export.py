from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, Query

from api.auth import require_auth
from fastapi.responses import StreamingResponse

from api.deps import get_db

router = APIRouter()


@router.get("/export", dependencies=[Depends(require_auth)])
def export_jobs(format: str = Query("csv", pattern="^(csv|json)$")):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM jobs ORDER BY relevance_score DESC"
        ).fetchall()

        if format == "json":
            data = [dict(r) for r in rows]
            for d in data:
                d["matched_keywords"] = (
                    d["matched_keywords"].split(",") if d["matched_keywords"] else []
                )
            content = json.dumps(data, indent=2, ensure_ascii=False)
            return StreamingResponse(
                io.BytesIO(content.encode("utf-8")),
                media_type="application/json",
                headers={"Content-Disposition": "attachment; filename=navy_jobs.json"},
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Score", "Title", "Company", "Location", "Seniority",
            "Type", "Reasoning", "Keywords", "URL", "Posted",
        ])
        for r in rows:
            writer.writerow([
                f"{r['relevance_score']:.2f}" if r["relevance_score"] else "",
                r["title"],
                r["company_name"],
                r["location"],
                r["seniority_level"] or "",
                r["employment_type"] or "",
                r["score_reasoning"] or "",
                r["matched_keywords"] or "",
                r["job_url"],
                r["posted_date"] or "",
            ])

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=navy_jobs.csv"},
        )
    finally:
        db.close()
