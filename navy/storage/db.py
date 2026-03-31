from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from navy.models import Company, Job, ScoredJob

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                linkedin_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company_name TEXT,
                company_linkedin_url TEXT,
                location TEXT,
                job_url TEXT,
                description TEXT,
                seniority_level TEXT,
                employment_type TEXT,
                posted_date TEXT,
                relevance_score REAL,
                score_reasoning TEXT,
                matched_keywords TEXT,
                first_seen_at TEXT DEFAULT (datetime('now')),
                last_seen_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS companies (
                linkedin_url TEXT PRIMARY KEY,
                name TEXT,
                employee_count INTEGER,
                size_category TEXT,
                industry TEXT,
                headquarters TEXT,
                source TEXT,
                fetched_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT,
                completed_at TEXT,
                jobs_found INTEGER DEFAULT 0,
                jobs_new INTEGER DEFAULT 0,
                jobs_passed_filter INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            );
            """
        )
        self.conn.commit()

    def is_duplicate(self, linkedin_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM jobs WHERE linkedin_id = ?", (linkedin_id,)
        ).fetchone()
        return row is not None

    def get_existing_ids(self, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        rows = self.conn.execute(
            f"SELECT linkedin_id FROM jobs WHERE linkedin_id IN ({placeholders})",
            ids,
        ).fetchall()
        return {row["linkedin_id"] for row in rows}

    def upsert_job(self, scored_job: ScoredJob) -> None:
        job = scored_job.job
        self.conn.execute(
            """
            INSERT INTO jobs (
                linkedin_id, title, company_name, company_linkedin_url,
                location, job_url, description, seniority_level,
                employment_type, posted_date, relevance_score,
                score_reasoning, matched_keywords
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(linkedin_id) DO UPDATE SET
                last_seen_at = datetime('now'),
                relevance_score = excluded.relevance_score,
                score_reasoning = excluded.score_reasoning,
                matched_keywords = excluded.matched_keywords
            """,
            (
                job.linkedin_id,
                job.title,
                job.company_name,
                job.company_linkedin_url,
                job.location,
                job.job_url,
                job.description,
                job.seniority_level,
                job.employment_type,
                job.posted_date,
                scored_job.relevance_score,
                scored_job.score_reasoning,
                ",".join(scored_job.matched_keywords),
            ),
        )
        self.conn.commit()

    def save_jobs_batch(self, scored_jobs: list[ScoredJob]) -> None:
        for sj in scored_jobs:
            self.upsert_job(sj)

    def get_cached_company(self, linkedin_url: str, max_age_days: int = 7) -> Company | None:
        row = self.conn.execute(
            "SELECT * FROM companies WHERE linkedin_url = ?", (linkedin_url,)
        ).fetchone()
        if not row:
            return None

        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if datetime.now() - fetched_at > timedelta(days=max_age_days):
            return None

        return Company(
            name=row["name"],
            linkedin_url=row["linkedin_url"],
            employee_count=row["employee_count"],
            size_category=row["size_category"],
            industry=row["industry"],
            headquarters=row["headquarters"],
            source=row["source"],
        )

    def save_company(self, company: Company) -> None:
        if not company.linkedin_url:
            return
        self.conn.execute(
            """
            INSERT INTO companies (
                linkedin_url, name, employee_count, size_category,
                industry, headquarters, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(linkedin_url) DO UPDATE SET
                employee_count = excluded.employee_count,
                size_category = excluded.size_category,
                industry = excluded.industry,
                fetched_at = datetime('now')
            """,
            (
                company.linkedin_url,
                company.name,
                company.employee_count,
                company.size_category,
                company.industry,
                company.headquarters,
                company.source,
            ),
        )
        self.conn.commit()

    def start_run(self) -> int:
        cursor = self.conn.execute(
            "INSERT INTO runs (started_at, status) VALUES (datetime('now'), 'running')"
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def complete_run(
        self,
        run_id: int,
        jobs_found: int,
        jobs_new: int,
        jobs_passed_filter: int,
        status: str = "success",
    ) -> None:
        self.conn.execute(
            """
            UPDATE runs SET
                completed_at = datetime('now'),
                jobs_found = ?,
                jobs_new = ?,
                jobs_passed_filter = ?,
                status = ?
            WHERE id = ?
            """,
            (jobs_found, jobs_new, jobs_passed_filter, status, run_id),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
