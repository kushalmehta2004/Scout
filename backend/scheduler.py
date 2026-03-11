"""
Scrape job scheduler. Runs Remotive and We Work Remotely scrapers on an interval,
merges results, deduplicates, and inserts into the DB. One failing source does not stop others.
"""

import asyncio
import logging
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from db.database import SessionLocal
from db.listings import insert_listings_deduplicated
from scrapers.base import ListingRow
from scrapers.remotive import fetch_remotive_listings
from scrapers.weworkremotely import fetch_weworkremotely_listings
from scrapers.remoteok import fetch_remoteok_listings
from scrapers.indeed import fetch_indeed_listings

logger = logging.getLogger(__name__)

# Run scrape every 12 hours (per PRD)
SCRAPE_INTERVAL_HOURS = 12
_scheduler: Optional[BackgroundScheduler] = None


def _run_remotive_sync() -> List[ListingRow]:
    """Run async Remotive fetcher from sync context (e.g. scheduler thread)."""
    try:
        return asyncio.run(fetch_remotive_listings())
    except Exception as e:
        logger.exception("Remotive scrape failed: %s", e)
        return []


def run_scrape_job() -> tuple[int, int]:
    """
    Run all scrapers, merge results, dedupe and insert into DB.
    Returns (total_inserted, total_duplicates). Logs per-source errors without failing.
    """
    all_rows: List[ListingRow] = []

    # We Work Remotely (sync)
    try:
        wwr = fetch_weworkremotely_listings()
        all_rows.extend(wwr)
        logger.info("We Work Remotely: fetched %d listings", len(wwr))
    except Exception as e:
        logger.exception("We Work Remotely scrape failed: %s", e)

    # Remotive (async, run in new event loop)
    try:
        remotive = _run_remotive_sync()
        all_rows.extend(remotive)
        logger.info("Remotive: fetched %d listings", len(remotive))
    except Exception as e:
        logger.exception("Remotive scrape failed: %s", e)

    # RemoteOK (sync)
    try:
        ro = fetch_remoteok_listings()
        all_rows.extend(ro)
        logger.info("RemoteOK: fetched %d listings", len(ro))
    except Exception as e:
        logger.exception("RemoteOK scrape failed: %s", e)

    # Indeed RSS (sync)
    try:
        indeed = fetch_indeed_listings()
        all_rows.extend(indeed)
        logger.info("Indeed: fetched %d listings", len(indeed))
    except Exception as e:
        logger.exception("Indeed scrape failed: %s", e)

    if not all_rows:
        logger.warning("No listings from any source")
        return 0, 0

    db = SessionLocal()
    try:
        inserted, duplicates = insert_listings_deduplicated(db, all_rows)
        db.commit()
        logger.info("Scrape job finished: inserted=%d, duplicates=%d", inserted, duplicates)
        return inserted, duplicates
    except Exception as e:
        db.rollback()
        logger.exception("DB insert failed: %s", e)
        raise
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler that runs the scrape job every SCRAPE_INTERVAL_HOURS."""
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(run_scrape_job, "interval", hours=SCRAPE_INTERVAL_HOURS, id="scrape_listings")
    _scheduler.start()
    logger.info("Scheduler started: scrape job every %d hours", SCRAPE_INTERVAL_HOURS)


def stop_scheduler() -> None:
    """Stop the background scheduler. Safe to call if not started."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")
