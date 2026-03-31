from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from navy.config import OutputConfig
from navy.models import ScoredJob

logger = logging.getLogger(__name__)


def _ensure_dir(path: str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_csv(scored_jobs: list[ScoredJob], output_dir: str) -> str:
    dir_path = _ensure_dir(output_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = dir_path / f"navy_jobs_{timestamp}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Relevance Score",
                "Title",
                "Company",
                "Location",
                "Employee Count",
                "Company Size",
                "Seniority",
                "Type",
                "Score Reasoning",
                "Matched Keywords",
                "Job URL",
                "Posted Date",
            ]
        )
        for sj in scored_jobs:
            company = sj.company
            writer.writerow(
                [
                    f"{sj.relevance_score:.2f}",
                    sj.job.title,
                    sj.job.company_name,
                    sj.job.location,
                    company.employee_count if company else "",
                    company.size_category if company else "unknown",
                    sj.job.seniority_level or "",
                    sj.job.employment_type or "",
                    sj.score_reasoning,
                    ", ".join(sj.matched_keywords),
                    sj.job.job_url,
                    sj.job.posted_date or "",
                ]
            )

    logger.info(f"CSV report saved: {filename}")
    return str(filename)


def generate_json(scored_jobs: list[ScoredJob], output_dir: str) -> str:
    dir_path = _ensure_dir(output_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = dir_path / f"navy_jobs_{timestamp}.json"

    data = []
    for sj in scored_jobs:
        entry = {
            "relevance_score": sj.relevance_score,
            "score_reasoning": sj.score_reasoning,
            "matched_keywords": sj.matched_keywords,
            "job": {
                "linkedin_id": sj.job.linkedin_id,
                "title": sj.job.title,
                "company_name": sj.job.company_name,
                "location": sj.job.location,
                "job_url": sj.job.job_url,
                "posted_date": sj.job.posted_date,
                "seniority_level": sj.job.seniority_level,
                "employment_type": sj.job.employment_type,
            },
            "company": None,
        }
        if sj.company:
            entry["company"] = {
                "name": sj.company.name,
                "employee_count": sj.company.employee_count,
                "size_category": sj.company.size_category,
                "industry": sj.company.industry,
                "headquarters": sj.company.headquarters,
                "source": sj.company.source,
            }
        data.append(entry)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"JSON report saved: {filename}")
    return str(filename)


def print_summary(scored_jobs: list[ScoredJob], top_n: int = 15) -> None:
    print("\n" + "=" * 80)
    print(f"  NAVY JOB SEARCH RESULTS — Top {min(top_n, len(scored_jobs))} of {len(scored_jobs)} jobs")
    print("=" * 80)

    for i, sj in enumerate(scored_jobs[:top_n]):
        size = ""
        if sj.company:
            emp = sj.company.employee_count
            cat = sj.company.size_category or ""
            size = f" [{cat}" + (f", ~{emp} emp" if emp else "") + "]"

        print(f"\n  {i + 1:2d}. [{sj.relevance_score:.2f}] {sj.job.title}")
        print(f"      {sj.job.company_name}{size} — {sj.job.location}")
        if sj.score_reasoning:
            print(f"      > {sj.score_reasoning}")
        print(f"      {sj.job.job_url}")

    print("\n" + "=" * 80)


def generate_report(
    scored_jobs: list[ScoredJob], config: OutputConfig
) -> list[str]:
    files = []
    project_root = Path(__file__).parent.parent.parent
    output_dir = str(project_root / config.output_dir)

    if "csv" in config.formats:
        files.append(generate_csv(scored_jobs, output_dir))
    if "json" in config.formats:
        files.append(generate_json(scored_jobs, output_dir))

    print_summary(scored_jobs)
    return files
