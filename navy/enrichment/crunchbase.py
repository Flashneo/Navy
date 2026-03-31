from __future__ import annotations

import logging

import requests

from navy.models import Company

logger = logging.getLogger(__name__)

CRUNCHBASE_SEARCH_URL = "https://api.crunchbase.com/api/v4/autocompletes"
CRUNCHBASE_ORG_URL = "https://api.crunchbase.com/api/v4/entities/organizations/{permalink}"


def _classify_size(employee_count: int | None) -> str:
    if employee_count is None:
        return "unknown"
    if employee_count <= 50:
        return "startup"
    if employee_count <= 500:
        return "medium"
    return "large"


def _parse_employee_range(range_str: str) -> int | None:
    mapping = {
        "c_00001_00010": 5,
        "c_00011_00050": 30,
        "c_00051_00100": 75,
        "c_00101_00250": 175,
        "c_00251_00500": 375,
        "c_00501_01000": 750,
        "c_01001_05000": 3000,
        "c_05001_10000": 7500,
        "c_10001_max": 15000,
    }
    return mapping.get(range_str)


def fetch_company_from_crunchbase(
    company_name: str, api_key: str
) -> Company | None:
    if not api_key:
        return None

    company = Company(name=company_name, source="crunchbase")

    try:
        # Step 1: Search for the company
        search_resp = requests.get(
            CRUNCHBASE_SEARCH_URL,
            params={
                "query": company_name,
                "collection_ids": "organizations",
                "limit": 1,
                "user_key": api_key,
            },
            timeout=15,
        )
        search_resp.raise_for_status()
        entities = search_resp.json().get("entities", [])
        if not entities:
            return None

        permalink = entities[0].get("identifier", {}).get("permalink")
        if not permalink:
            return None

        # Step 2: Get organization details
        org_resp = requests.get(
            CRUNCHBASE_ORG_URL.format(permalink=permalink),
            params={
                "field_ids": "num_employees_enum,short_description,categories,location_identifiers",
                "user_key": api_key,
            },
            timeout=15,
        )
        org_resp.raise_for_status()
        props = org_resp.json().get("properties", {})

        emp_enum = props.get("num_employees_enum")
        if emp_enum:
            company.employee_count = _parse_employee_range(emp_enum)

        categories = props.get("categories", [])
        if categories:
            company.industry = categories[0].get("value", "")

        locations = props.get("location_identifiers", [])
        if locations:
            company.headquarters = locations[0].get("value", "")

        company.size_category = _classify_size(company.employee_count)

        logger.debug(
            f"Crunchbase: {company_name} -> {company.employee_count} employees "
            f"({company.size_category})"
        )
        return company

    except Exception as e:
        logger.warning(f"Crunchbase lookup failed for {company_name}: {e}")
        return None
