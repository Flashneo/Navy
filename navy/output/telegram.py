from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

import requests

from navy.models import ScoredJob

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"
DB_PATH = Path(__file__).parent.parent.parent / "data" / "navy.db"


# ── Subscriber storage ──────────────────────────────────────────────

def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS telegram_subscribers (
            chat_id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TEXT DEFAULT (datetime('now'))
        )"""
    )
    conn.commit()
    return conn


def add_subscriber(chat_id: str, username: str = "", first_name: str = "") -> None:
    db = _get_db()
    db.execute(
        """INSERT INTO telegram_subscribers (chat_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name""",
        (chat_id, username, first_name),
    )
    db.commit()
    db.close()
    logger.info(f"Telegram subscriber added: {chat_id} ({first_name or username})")


def remove_subscriber(chat_id: str) -> None:
    db = _get_db()
    db.execute("DELETE FROM telegram_subscribers WHERE chat_id = ?", (chat_id,))
    db.commit()
    db.close()
    logger.info(f"Telegram subscriber removed: {chat_id}")


def get_all_subscribers() -> list[str]:
    db = _get_db()
    rows = db.execute("SELECT chat_id FROM telegram_subscribers").fetchall()
    db.close()
    return [r[0] for r in rows]


# ── Message sending ─────────────────────────────────────────────────

def send_message(token: str, chat_id: str, text: str) -> bool:
    try:
        resp = requests.post(
            f"{TELEGRAM_API.format(token=token)}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning(f"Telegram send error ({chat_id}): {resp.status_code}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Telegram send failed ({chat_id}): {e}")
        return False


def _format_job(job: ScoredJob, index: int) -> str:
    score_pct = int(job.relevance_score * 100)
    icon = "🟢" if score_pct >= 80 else "🟡" if score_pct >= 60 else "🔴"

    lines = [
        f"{icon} <b>{index}. {job.job.title}</b> ({score_pct}%)",
        f"🏢 {job.job.company_name}",
        f"📍 {job.job.location}",
    ]
    if job.job.seniority_level:
        lines.append(f"📊 {job.job.seniority_level}")
    if job.matched_keywords:
        lines.append(f"🏷 {', '.join(job.matched_keywords[:5])}")
    if job.score_reasoning and job.score_reasoning != "Keyword-based fallback scoring":
        lines.append(f"💡 <i>{job.score_reasoning[:100]}</i>")
    lines.append(f'🔗 <a href="{job.job.job_url}">Apply on LinkedIn</a>')
    return "\n".join(lines)


def notify_new_jobs(
    token: str,
    jobs: list[ScoredJob],
    total_found: int,
    total_new: int,
    chat_id: str = "",
) -> None:
    if not token:
        logger.debug("Telegram bot token not set, skipping")
        return

    # Send to specific chat_id or all subscribers
    if chat_id:
        recipients = [chat_id]
    else:
        recipients = get_all_subscribers()

    if not recipients:
        logger.debug("No Telegram subscribers, skipping notification")
        return

    if not jobs:
        for cid in recipients:
            send_message(token, cid, "🔍 <b>Navy Job Search</b>\n\nNo new matching jobs found this run.")
        return

    header = (
        f"🚀 <b>Navy Job Search — New Results</b>\n\n"
        f"📊 Found: {total_found} | New: {total_new} | Matched: {len(jobs)}\n"
        f"{'─' * 30}"
    )

    top_jobs = jobs[:10]

    for cid in recipients:
        send_message(token, cid, header)

        for i in range(0, len(top_jobs), 3):
            batch = top_jobs[i : i + 3]
            parts = [_format_job(j, i + k + 1) for k, j in enumerate(batch)]
            send_message(token, cid, "\n\n".join(parts))

        if len(jobs) > 10:
            send_message(token, cid, f"... and {len(jobs) - 10} more jobs. Check the dashboard!")

    logger.info(f"Telegram: notified {len(recipients)} subscribers about {len(top_jobs)} jobs")


# ── Bot polling (runs in background thread) ─────────────────────────

def _poll_updates(token: str) -> None:
    """Long-poll Telegram for /start and /stop commands."""
    offset = 0
    logger.info("Telegram bot polling started")

    while True:
        try:
            resp = requests.get(
                f"{TELEGRAM_API.format(token=token)}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            )
            if resp.status_code != 200:
                logger.warning(f"Telegram getUpdates error: {resp.status_code}")
                continue

            data = resp.json()
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat = msg.get("chat", {})
                cid = str(chat.get("id", ""))
                user = msg.get("from", {})
                username = user.get("username", "")
                first_name = user.get("first_name", "")

                if not cid:
                    continue

                if text == "/start":
                    add_subscriber(cid, username, first_name)
                    send_message(
                        token, cid,
                        f"👋 Welcome{(' ' + first_name) if first_name else ''}!\n\n"
                        "You're now subscribed to <b>Navy Job Search</b> notifications.\n\n"
                        "You'll receive alerts when new matching jobs are found.\n\n"
                        "Commands:\n"
                        "/status — Check bot status\n"
                        "/stop — Unsubscribe from notifications",
                    )

                elif text == "/stop":
                    remove_subscriber(cid)
                    send_message(
                        token, cid,
                        "👋 You've been unsubscribed. Send /start to re-subscribe.",
                    )

                elif text == "/status":
                    subs = get_all_subscribers()
                    send_message(
                        token, cid,
                        f"🤖 <b>Navy Bot Status</b>\n\n"
                        f"Subscribers: {len(subs)}\n"
                        f"Your chat ID: <code>{cid}</code>\n"
                        f"Subscribed: {'Yes ✅' if cid in subs else 'No ❌'}",
                    )

        except requests.exceptions.ReadTimeout:
            continue
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            import time
            time.sleep(5)


def start_bot(token: str) -> threading.Thread | None:
    """Start the Telegram bot in a background thread."""
    if not token or token == "your-bot-token-here":
        logger.debug("Telegram bot token not configured, bot not started")
        return None

    thread = threading.Thread(target=_poll_updates, args=(token,), daemon=True)
    thread.start()
    logger.info("Telegram bot started in background")
    return thread
