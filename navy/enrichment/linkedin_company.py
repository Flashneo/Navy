from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup

from navy.models import Company
from navy.scraper.http_client import RateLimitedClient

logger = logging.getLogger(__name__)

EMPLOYEE_RANGES = {
    "1-10": 5,
    "2-10": 6,
    "11-50": 30,
    "51-200": 125,
    "201-500": 350,
    "501-1,000": 750,
    "501-1000": 750,
    "1,001-5,000": 3000,
    "1001-5000": 3000,
    "5,001-10,000": 7500,
    "5001-10000": 7500,
    "10,001+": 15000,
    "10001+": 15000,
}


def _classify_size(employee_count: int | None) -> str:
    if employee_count is None:
        return "unknown"
    if employee_count <= 50:
        return "startup"
    if employee_count <= 500:
        return "medium"
    return "large"


def _parse_employee_count(text: str) -> int | None:
    for range_str, midpoint in EMPLOYEE_RANGES.items():
        if range_str in text:
            return midpoint

    numbers = re.findall(r"[\d,]+", text)
    if numbers:
        try:
            return int(numbers[0].replace(",", ""))
        except ValueError:
            pass
    return None


def fetch_company_info(
    client: RateLimitedClient, company_url: str, company_name: str
) -> Company:
    company = Company(name=company_name, linkedin_url=company_url, source="linkedin")

    if not company_url:
        company.size_category = "unknown"
        return company

    about_url = company_url.rstrip("/") + "/about/"

    try:
        response = client.get(about_url)
        soup = BeautifulSoup(response.text, "lxml")

        # Try JSON-LD first
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string or "")
                if isinstance(data, list):
                    data = data[0]
                num_employees = data.get("numberOfEmployees", {})
                if isinstance(num_employees, dict):
                    value = num_employees.get("value")
                    if value:
                        company.employee_count = int(value)
                elif isinstance(num_employees, (int, str)):
                    company.employee_count = int(num_employees)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

        # Fallback: parse HTML for employee count text
        if company.employee_count is None:
            page_text = soup.get_text()
            for line in page_text.split("\n"):
                line = line.strip()
                if "employees" in line.lower() or "company size" in line.lower():
                    count = _parse_employee_count(line)
                    if count:
                        company.employee_count = count
                        break

        # Try to get industry
        industry_section = soup.find(string=re.compile(r"industr", re.I))
        if industry_section:
            parent = industry_section.find_parent()
            if parent:
                sibling = parent.find_next_sibling()
                if sibling:
                    company.industry = sibling.get_text(strip=True)

        company.size_category = _classify_size(company.employee_count)
        logger.debug(
            f"Company {company_name}: {company.employee_count} employees "
            f"({company.size_category})"
        )

    except Exception as e:
        logger.warning(f"Failed to fetch company info for {company_name}: {e}")
        company.size_category = "unknown"

    return company
