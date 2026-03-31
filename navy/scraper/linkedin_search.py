from __future__ import annotations

import logging
import re
import threading

from bs4 import BeautifulSoup

from navy.models import Job, SearchQuery
from navy.scraper.http_client import RateLimitedClient

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
RESULTS_PER_PAGE = 25
MAX_PAGES = 10


def build_search_queries(
    keywords: list[str],
    locations: list[str],
    time_filters: list[str],
    experience_level: str,
    remote_filters: list[str],
) -> list[SearchQuery]:
    queries = []
    for kw in keywords:
        for loc in locations:
            for tf in time_filters:
                for rf in remote_filters:
                    queries.append(
                        SearchQuery(
                            keywords=kw,
                            location=loc,
                            time_filter=tf,
                            experience_level=experience_level,
                            remote_filter=rf,
                        )
                    )
    return queries


def _extract_job_id(url: str) -> str | None:
    # Match job ID at end of URL: /jobs/view/some-title-at-company-1234567890
    match = re.search(r"-(\d{7,})(?:\?|$)", url)
    if match:
        return match.group(1)
    match = re.search(r"/view/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"currentJobId=(\d+)", url)
    if match:
        return match.group(1)
    return None


def _parse_search_results(html: str) -> list[Job]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    cards = soup.find_all("div", class_="base-card")
    if not cards:
        cards = soup.find_all("li")

    for card in cards:
        try:
            title_el = card.find("h3", class_="base-search-card__title")
            if not title_el:
                title_el = card.find("h3")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            company_el = card.find("h4", class_="base-search-card__subtitle")
            if not company_el:
                company_el = card.find("h4")
            company_name = company_el.get_text(strip=True) if company_el else "Unknown"

            company_url = None
            if company_el:
                company_link = company_el.find("a")
                if company_link and company_link.get("href"):
                    company_url = company_link["href"].split("?")[0]

            location_el = card.find("span", class_="job-search-card__location")
            location = location_el.get_text(strip=True) if location_el else "Unknown"

            job_url = ""
            link_el = card.find("a", class_="base-card__full-link")
            if not link_el:
                link_el = card.find("a", href=True)
            if link_el and link_el.get("href"):
                job_url = link_el["href"].split("?")[0]

            linkedin_id = _extract_job_id(job_url) if job_url else None
            if not linkedin_id:
                continue

            date_el = card.find("time")
            posted_date = date_el.get("datetime") if date_el else None

            jobs.append(
                Job(
                    linkedin_id=linkedin_id,
                    title=title,
                    company_name=company_name,
                    location=location,
                    job_url=job_url,
                    company_linkedin_url=company_url,
                    posted_date=posted_date,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse job card: {e}")
            continue

    return jobs


def search_jobs(
    client: RateLimitedClient,
    query: SearchQuery,
    max_pages: int = MAX_PAGES,
) -> list[Job]:
    all_jobs = []
    seen_ids: set[str] = set()

    for page in range(max_pages):
        params = {
            "keywords": query.keywords,
            "location": query.location,
            "f_TPR": query.time_filter,
            "f_E": query.experience_level,
            "f_WT": query.remote_filter,
            "start": page * RESULTS_PER_PAGE,
        }

        try:
            response = client.get(SEARCH_URL, params=params)
            if not response.text.strip():
                logger.debug(f"Empty response at page {page}, stopping pagination")
                break

            jobs = _parse_search_results(response.text)
            if not jobs:
                logger.debug(f"No jobs found at page {page}, stopping pagination")
                break

            new_count = 0
            for job in jobs:
                if job.linkedin_id not in seen_ids:
                    seen_ids.add(job.linkedin_id)
                    all_jobs.append(job)
                    new_count += 1

            logger.info(
                f"[{query.keywords}][{query.location}] Page {page}: "
                f"{len(jobs)} results, {new_count} new"
            )

            if len(jobs) < RESULTS_PER_PAGE:
                break

        except Exception as e:
            logger.error(f"Search failed at page {page}: {e}")
            break

    return all_jobs


def search_all(
    client: RateLimitedClient,
    keywords: list[str],
    locations: list[str],
    time_filters: list[str],
    experience_level: str,
    remote_filters: list[str],
    stop_event: threading.Event | None = None,
    progress: dict | None = None,
) -> list[Job]:
    queries = build_search_queries(
        keywords, locations, time_filters, experience_level, remote_filters
    )

    all_jobs: list[Job] = []
    seen_ids: set[str] = set()

    logger.info(f"Running {len(queries)} search combinations")

    for i, query in enumerate(queries):
        if stop_event and stop_event.is_set():
            logger.info("Search stopped by user.")
            break

        logger.info(
            f"[{i + 1}/{len(queries)}] Searching: '{query.keywords}' "
            f"in '{query.location}' (time={query.time_filter}, remote={query.remote_filter})"
        )
        jobs = search_jobs(client, query)
        new_count = 0
        for job in jobs:
            if job.linkedin_id not in seen_ids:
                seen_ids.add(job.linkedin_id)
                all_jobs.append(job)
                new_count += 1
        logger.info(f"  Found {len(jobs)} jobs, {new_count} new (total: {len(all_jobs)})")
        if progress is not None:
            progress["jobs_found"] = len(all_jobs)

    logger.info(f"Total unique jobs found: {len(all_jobs)}")
    return all_jobs
