from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "navy.db"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
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
        CREATE TABLE IF NOT EXISTS telegram_subscribers (
            chat_id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TEXT DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn


def load_config_raw() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config_raw(data: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
