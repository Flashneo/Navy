from __future__ import annotations

import argparse
import logging
import sys
import threading
from pathlib import Path

from navy.config import load_config
from navy.enrichment.company_enricher import enrich_companies_batch
from navy.filtering.engine import apply_filters
from navy.models import ScoredJob
from navy.output.report import generate_report
from navy.output.telegram import notify_new_jobs
from navy.scraper.http_client import RateLimitedClient
from navy.scraper.linkedin_detail import fetch_details_batch
from navy.scraper.linkedin_search import search_all
from navy.scoring.ai_scorer import score_jobs
from navy.storage.db import Database

logger = logging.getLogger("navy")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def run_pipeline(
    config_path: str = "config.yaml",
    dry_run: bool = False,
    skip_enrichment: bool = False,
    verbose: bool = False,
    stop_event: threading.Event | None = None,
    progress: dict | None = None,
) -> list[ScoredJob]:
    setup_logging(verbose)
    config = load_config(config_path)

    def _update(step: str, **kwargs: int) -> None:
        if progress is not None:
            progress["step"] = step
            progress.update(kwargs)

    project_root = Path(__file__).parent.parent
    db_path = str(project_root / config.storage.db_path)
    db = Database(db_path)
    run_id = db.start_run()

    client = RateLimitedClient(config.rate_limiting)

    def _stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    try:
        # Step 1: Search LinkedIn
        _update("Searching LinkedIn...")
        logger.info("=" * 60)
        logger.info("STEP 1: Searching LinkedIn for jobs...")
        logger.info("=" * 60)
        jobs = search_all(
            client,
            keywords=config.search.keywords,
            locations=config.search.locations,
            time_filters=config.search.time_filters,
            experience_level=config.search.experience_level,
            remote_filters=config.search.remote_filters,
            stop_event=stop_event,
            progress=progress,
        )

        if _stopped():
            logger.info("Run stopped by user.")
            db.complete_run(run_id, len(jobs), 0, 0, status="stopped")
            return []

        if not jobs:
            logger.warning("No jobs found. Try broadening your search criteria.")
            db.complete_run(run_id, 0, 0, 0, status="no_results")
            return []

        total_found = len(jobs)
        _update("Deduplicating...", jobs_found=total_found)
        logger.info(f"Found {total_found} unique jobs")

        # Step 2: Deduplicate against DB
        logger.info("=" * 60)
        logger.info("STEP 2: Deduplicating against previous runs...")
        logger.info("=" * 60)
        existing_ids = db.get_existing_ids([j.linkedin_id for j in jobs])
        new_jobs = [j for j in jobs if j.linkedin_id not in existing_ids]
        _update("Deduplicating...", jobs_found=total_found, jobs_new=len(new_jobs))
        logger.info(f"{len(new_jobs)} new jobs (skipped {len(existing_ids)} duplicates)")

        if not new_jobs:
            logger.info("No new jobs since last run.")
            db.complete_run(run_id, total_found, 0, 0, status="no_new")
            return []

        if _stopped():
            logger.info("Run stopped by user.")
            db.complete_run(run_id, total_found, len(new_jobs), 0, status="stopped")
            return []

        # Step 3: Fetch job details
        _update("Fetching details...", jobs_found=total_found, jobs_new=len(new_jobs))
        logger.info("=" * 60)
        logger.info("STEP 3: Fetching job details...")
        logger.info("=" * 60)
        new_jobs = fetch_details_batch(client, new_jobs, stop_event=stop_event)

        if _stopped():
            logger.info("Run stopped by user during detail fetch.")
            db.complete_run(run_id, total_found, len(new_jobs), 0, status="stopped")
            return []

        # Step 4: Enrich companies
        companies = {}
        if not skip_enrichment:
            _update("Enriching companies...", jobs_found=total_found, jobs_new=len(new_jobs))
            logger.info("=" * 60)
            logger.info("STEP 4: Enriching company data...")
            logger.info("=" * 60)
            companies = enrich_companies_batch(
                client, db, new_jobs, config.crunchbase_api_key
            )
        else:
            logger.info("STEP 4: Skipping company enrichment")

        if _stopped():
            logger.info("Run stopped by user.")
            db.complete_run(run_id, total_found, len(new_jobs), 0, status="stopped")
            return []

        # Step 5: Score with AI
        _update("Scoring jobs...", jobs_found=total_found, jobs_new=len(new_jobs))
        logger.info("=" * 60)
        logger.info("STEP 5: Scoring job relevance...")
        logger.info("=" * 60)
        api_key = (
            config.anthropic_api_key
            if config.scoring.provider == "anthropic"
            else config.openai_api_key
        )
        scored_jobs = score_jobs(new_jobs, config.scoring, api_key, dry_run=dry_run)

        # Attach company data
        for sj in scored_jobs:
            sj.company = companies.get(sj.job.linkedin_id)

        # Step 6: Filter
        _update("Filtering...", jobs_found=total_found, jobs_new=len(new_jobs))
        logger.info("=" * 60)
        logger.info("STEP 6: Applying filters...")
        logger.info("=" * 60)
        filtered = apply_filters(
            scored_jobs,
            config.filtering,
            min_score=config.scoring.min_relevance_score,
        )

        # Step 7: Save & Report
        _update("Saving results...", jobs_found=total_found, jobs_new=len(new_jobs), jobs_passed=len(filtered))
        logger.info("=" * 60)
        logger.info("STEP 7: Saving results and generating report...")
        logger.info("=" * 60)
        db.save_jobs_batch(filtered)
        report_files = generate_report(filtered, config.output)

        # Step 8: Telegram notification
        if config.telegram_bot_token:
            logger.info("Sending Telegram notifications...")
            notify_new_jobs(
                token=config.telegram_bot_token,
                jobs=filtered,
                total_found=total_found,
                total_new=len(new_jobs),
            )

        db.complete_run(
            run_id,
            jobs_found=total_found,
            jobs_new=len(new_jobs),
            jobs_passed_filter=len(filtered),
            status="success",
        )

        logger.info(f"Run complete! {len(filtered)} jobs passed all filters.")
        for f in report_files:
            logger.info(f"Report: {f}")

        return filtered

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        db.complete_run(run_id, 0, 0, 0, status="failed")
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Navy — LinkedIn Job Search AI Agent"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without AI scoring (uses keyword fallback)",
    )
    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip company data enrichment",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    results = run_pipeline(
        config_path=args.config,
        dry_run=args.dry_run,
        skip_enrichment=args.skip_enrichment,
        verbose=args.verbose,
    )

    if not results:
        sys.exit(0)

    print(f"\n✓ Found {len(results)} matching jobs. Check the output/ directory for reports.")


if __name__ == "__main__":
    main()
