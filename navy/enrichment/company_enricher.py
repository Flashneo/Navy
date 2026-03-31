from __future__ import annotations

import logging

from navy.enrichment.crunchbase import fetch_company_from_crunchbase
from navy.enrichment.linkedin_company import fetch_company_info
from navy.models import Company, Job
from navy.scraper.http_client import RateLimitedClient
from navy.storage.db import Database

logger = logging.getLogger(__name__)


def enrich_company(
    client: RateLimitedClient,
    db: Database,
    job: Job,
    crunchbase_api_key: str = "",
) -> Company:
    # 1. Check cache
    if job.company_linkedin_url:
        cached = db.get_cached_company(job.company_linkedin_url)
        if cached:
            logger.debug(f"Cache hit for {job.company_name}")
            return cached

    # 2. Try LinkedIn company page
    company = fetch_company_info(client, job.company_linkedin_url or "", job.company_name)

    # 3. If LinkedIn didn't yield employee count, try Crunchbase
    if company.employee_count is None and crunchbase_api_key:
        logger.debug(f"Trying Crunchbase for {job.company_name}")
        cb_company = fetch_company_from_crunchbase(job.company_name, crunchbase_api_key)
        if cb_company and cb_company.employee_count is not None:
            company.employee_count = cb_company.employee_count
            company.size_category = cb_company.size_category
            company.industry = cb_company.industry or company.industry
            company.headquarters = cb_company.headquarters or company.headquarters
            company.source = "crunchbase"

    # 4. Save to cache
    db.save_company(company)
    return company


def enrich_companies_batch(
    client: RateLimitedClient,
    db: Database,
    jobs: list[Job],
    crunchbase_api_key: str = "",
) -> dict[str, Company]:
    logger.info(f"Enriching company data for {len(jobs)} jobs...")
    companies: dict[str, Company] = {}
    seen_urls: dict[str, Company] = {}

    for i, job in enumerate(jobs):
        url_key = job.company_linkedin_url or job.company_name

        if url_key in seen_urls:
            companies[job.linkedin_id] = seen_urls[url_key]
            continue

        company = enrich_company(client, db, job, crunchbase_api_key)
        companies[job.linkedin_id] = company
        seen_urls[url_key] = company

        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i + 1}/{len(jobs)} companies enriched")

    logger.info(f"Finished enriching {len(companies)} companies")
    return companies
