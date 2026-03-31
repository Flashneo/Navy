from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    keywords: str
    location: str
    time_filter: str  # "r86400" (24h) or "r604800" (week)
    experience_level: str  # "4" = Mid-Senior
    remote_filter: str  # "2" = Remote, "3" = Hybrid


@dataclass
class Job:
    linkedin_id: str
    title: str
    company_name: str
    location: str
    job_url: str
    company_linkedin_url: str | None = None
    posted_date: str | None = None
    description: str | None = None
    seniority_level: str | None = None
    employment_type: str | None = None


@dataclass
class Company:
    name: str
    linkedin_url: str | None = None
    employee_count: int | None = None
    size_category: str | None = None  # "startup", "medium", "large", "unknown"
    industry: str | None = None
    headquarters: str | None = None
    source: str = "unknown"


@dataclass
class ScoredJob:
    job: Job
    company: Company | None = None
    relevance_score: float = 0.0
    score_reasoning: str = ""
    matched_keywords: list[str] = field(default_factory=list)
