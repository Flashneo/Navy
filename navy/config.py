from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class SearchConfig:
    keywords: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    time_filters: list[str] = field(default_factory=list)
    experience_level: str = "4"
    remote_filters: list[str] = field(default_factory=list)


@dataclass
class SizeRange:
    min: int = 0
    max: int = 0


@dataclass
class FilterConfig:
    company_size: dict[str, SizeRange] = field(default_factory=dict)
    allowed_categories: list[str] = field(default_factory=list)


@dataclass
class ScoringConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    user_profile: str = ""
    min_relevance_score: float = 0.5


@dataclass
class RateLimitConfig:
    requests_per_minute: int = 10
    retry_max: int = 3
    retry_backoff_base: float = 2.0
    jitter_min: float = 1.0
    jitter_max: float = 3.0


@dataclass
class StorageConfig:
    db_path: str = "data/navy.db"


@dataclass
class OutputConfig:
    formats: list[str] = field(default_factory=lambda: ["csv", "json"])
    output_dir: str = "output/"


@dataclass
class AppConfig:
    search: SearchConfig = field(default_factory=SearchConfig)
    filtering: FilterConfig = field(default_factory=FilterConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    # API keys loaded from environment
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    crunchbase_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


def load_config(config_path: str = "config.yaml") -> AppConfig:
    load_dotenv()

    project_root = Path(__file__).parent.parent
    full_path = project_root / config_path

    with open(full_path) as f:
        raw = yaml.safe_load(f)

    search_raw = raw.get("search", {})
    search = SearchConfig(
        keywords=search_raw.get("keywords", []),
        locations=search_raw.get("locations", []),
        time_filters=search_raw.get("time_filters", []),
        experience_level=search_raw.get("experience_level", "4"),
        remote_filters=search_raw.get("remote_filters", []),
    )

    filter_raw = raw.get("filtering", {})
    size_raw = filter_raw.get("company_size", {})
    company_size = {}
    for category, bounds in size_raw.items():
        company_size[category] = SizeRange(
            min=bounds.get("min", 0), max=bounds.get("max", 0)
        )
    filtering = FilterConfig(
        company_size=company_size,
        allowed_categories=filter_raw.get("allowed_categories", []),
    )

    score_raw = raw.get("scoring", {})
    scoring = ScoringConfig(
        provider=score_raw.get("provider", "openai"),
        model=score_raw.get("model", "gpt-4o-mini"),
        user_profile=score_raw.get("user_profile", ""),
        min_relevance_score=score_raw.get("min_relevance_score", 0.5),
    )

    rl_raw = raw.get("rate_limiting", {})
    rate_limiting = RateLimitConfig(
        requests_per_minute=rl_raw.get("requests_per_minute", 10),
        retry_max=rl_raw.get("retry_max", 3),
        retry_backoff_base=rl_raw.get("retry_backoff_base", 2.0),
        jitter_min=rl_raw.get("jitter_min", 1.0),
        jitter_max=rl_raw.get("jitter_max", 3.0),
    )

    storage_raw = raw.get("storage", {})
    storage = StorageConfig(db_path=storage_raw.get("db_path", "data/navy.db"))

    output_raw = raw.get("output", {})
    output = OutputConfig(
        formats=output_raw.get("formats", ["csv", "json"]),
        output_dir=output_raw.get("output_dir", "output/"),
    )

    return AppConfig(
        search=search,
        filtering=filtering,
        scoring=scoring,
        rate_limiting=rate_limiting,
        storage=storage,
        output=output,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        crunchbase_api_key=os.getenv("CRUNCHBASE_API_KEY", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
    )
