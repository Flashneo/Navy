from __future__ import annotations

import logging
import re
import threading

from bs4 import BeautifulSoup

from navy.models import Job
from navy.scraper.http_client import RateLimitedClient

logger = logging.getLogger(__name__)

DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"


def _clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "lxml")
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_job_detail(client: RateLimitedClient, job: Job) -> Job:
    url = DETAIL_URL.format(job_id=job.linkedin_id)

    try:
        response = client.get(url)
        soup = BeautifulSoup(response.text, "lxml")

        desc_el = soup.find("div", class_="show-more-less-html__markup")
        if desc_el:
            job.description = _clean_html(str(desc_el))

        criteria_list = soup.find("ul", class_="description__job-criteria-list")
        if criteria_list:
            items = criteria_list.find_all("li", class_="description__job-criteria-item")
            for item in items:
                header = item.find("h3")
                value = item.find("span", class_="description__job-criteria-text")
                if header and value:
                    header_text = header.get_text(strip=True).lower()
                    value_text = value.get_text(strip=True)
                    if "seniority" in header_text:
                        job.seniority_level = value_text
                    elif "employment" in header_text or "job type" in header_text:
                        job.employment_type = value_text

        logger.debug(f"Fetched detail for job {job.linkedin_id}: {job.title}")

    except Exception as e:
        logger.warning(f"Failed to fetch detail for job {job.linkedin_id}: {e}")

    return job


def fetch_details_batch(
    client: RateLimitedClient,
    jobs: list[Job],
    stop_event: threading.Event | None = None,
) -> list[Job]:
    logger.info(f"Fetching details for {len(jobs)} jobs...")
    for i, job in enumerate(jobs):
        if stop_event and stop_event.is_set():
            logger.info(f"Detail fetch stopped by user at {i}/{len(jobs)}.")
            break
        fetch_job_detail(client, job)
        if (i + 1) % 10 == 0:
            logger.info(f"  Progress: {i + 1}/{len(jobs)} job details fetched")
    logger.info(f"Finished fetching {len(jobs)} job details")
    return jobs
