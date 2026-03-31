from __future__ import annotations

from fastapi import APIRouter, Query

from api.deps import get_db

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    q: str = "",
    min_score: float = 0.0,
    size: str = "",
    page: int = 1,
    per_page: int = 20,
    sort_by: str = "relevance_score",
    sort_order: str = "desc",
):
    db = get_db()
    try:
        conditions = []
        params: list = []

        if q:
            conditions.append(
                "(title LIKE ? OR company_name LIKE ? OR description LIKE ?)"
            )
            like_q = f"%{q}%"
            params.extend([like_q, like_q, like_q])

        if min_score > 0:
            conditions.append("relevance_score >= ?")
            params.append(min_score)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        allowed_sorts = {
            "relevance_score", "title", "company_name", "location",
            "posted_date", "first_seen_at",
        }
        if sort_by not in allowed_sorts:
            sort_by = "relevance_score"
        order = "DESC" if sort_order == "desc" else "ASC"

        total = db.execute(
            f"SELECT COUNT(*) FROM jobs {where}", params
        ).fetchone()[0]

        offset = (page - 1) * per_page
        rows = db.execute(
            f"""SELECT * FROM jobs {where}
            ORDER BY {sort_by} {order}
            LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        jobs = []
        for r in rows:
            jobs.append({
                "linkedin_id": r["linkedin_id"],
                "title": r["title"],
                "company_name": r["company_name"],
                "company_linkedin_url": r["company_linkedin_url"],
                "location": r["location"],
                "job_url": r["job_url"],
                "seniority_level": r["seniority_level"],
                "employment_type": r["employment_type"],
                "posted_date": r["posted_date"],
                "relevance_score": r["relevance_score"],
                "score_reasoning": r["score_reasoning"],
                "matched_keywords": r["matched_keywords"].split(",") if r["matched_keywords"] else [],
                "first_seen_at": r["first_seen_at"],
                "last_seen_at": r["last_seen_at"],
            })

        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    finally:
        db.close()


@router.get("/jobs/{linkedin_id}")
def get_job(linkedin_id: str):
    db = get_db()
    try:
        row = db.execute(
            "SELECT * FROM jobs WHERE linkedin_id = ?", (linkedin_id,)
        ).fetchone()

        if not row:
            return {"error": "Job not found"}, 404

        company = None
        if row["company_linkedin_url"]:
            comp_row = db.execute(
                "SELECT * FROM companies WHERE linkedin_url = ?",
                (row["company_linkedin_url"],),
            ).fetchone()
            if comp_row:
                company = dict(comp_row)

        return {
            **dict(row),
            "matched_keywords": row["matched_keywords"].split(",") if row["matched_keywords"] else [],
            "company": company,
        }
    finally:
        db.close()
