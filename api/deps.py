from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "navy.db"
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def load_config_raw() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config_raw(data: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
