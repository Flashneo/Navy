from __future__ import annotations

import logging

from navy.config import FilterConfig
from navy.models import Company, ScoredJob

logger = logging.getLogger(__name__)


def filter_by_company_size(
    scored_jobs: list[ScoredJob],
    config: FilterConfig,
) -> list[ScoredJob]:
    if not config.allowed_categories:
        return scored_jobs

    passed = []
    for sj in scored_jobs:
        category = sj.company.size_category if sj.company else "unknown"
        if category in config.allowed_categories:
            passed.append(sj)
        else:
            logger.debug(
                f"Filtered out: {sj.job.title} at {sj.job.company_name} "
                f"(size: {category})"
            )
    return passed


def filter_by_score(
    scored_jobs: list[ScoredJob],
    min_score: float,
) -> list[ScoredJob]:
    return [sj for sj in scored_jobs if sj.relevance_score >= min_score]


def deduplicate(
    scored_jobs: list[ScoredJob],
    existing_ids: set[str],
) -> list[ScoredJob]:
    new_jobs = []
    for sj in scored_jobs:
        if sj.job.linkedin_id not in existing_ids:
            new_jobs.append(sj)
    return new_jobs


def apply_filters(
    scored_jobs: list[ScoredJob],
    filter_config: FilterConfig,
    min_score: float,
    existing_ids: set[str] | None = None,
) -> list[ScoredJob]:
    total = len(scored_jobs)

    # Dedup
    if existing_ids:
        scored_jobs = deduplicate(scored_jobs, existing_ids)
        logger.info(f"After dedup: {len(scored_jobs)}/{total} jobs")

    # Company size
    scored_jobs = filter_by_company_size(scored_jobs, filter_config)
    logger.info(f"After company size filter: {len(scored_jobs)} jobs")

    # Score threshold
    scored_jobs = filter_by_score(scored_jobs, min_score)
    logger.info(f"After score filter (>={min_score}): {len(scored_jobs)} jobs")

    # Sort by relevance
    scored_jobs.sort(key=lambda sj: sj.relevance_score, reverse=True)

    return scored_jobs
