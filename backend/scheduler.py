"""
Scrape job scheduler. Runs Indeed scraper on an interval,
merges results, deduplicates, and inserts into the DB.
"""

import logging
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler

from db.database import SessionLocal
from db.listings import insert_listings_deduplicated
from scrapers.base import ListingRow
from scrapers.indeed import fetch_indeed_listings
from scrapers.hacker_news import fetch_hn_listings
from scrapers.ai_jobs import fetch_aijobs_listings
from scrapers.huggingface import fetch_huggingface_listings
from scrapers.ycombinator import fetch_ycombinator_listings

logger = logging.getLogger(__name__)

# Run scrape every 12 hours (per PRD)
SCRAPE_INTERVAL_HOURS = 12
_scheduler: Optional[BackgroundScheduler] = None


def run_scrape_job() -> tuple[int, int]:
    """
    Run all scrapers, merge results, dedupe and insert into DB.
    Returns (total_inserted, total_duplicates). Logs per-source errors without failing.
    """
    all_rows: List[ListingRow] = []

    # Indeed RSS (sync)
    try:
        indeed = fetch_indeed_listings()
        all_rows.extend(indeed)
        logger.info("Indeed: fetched %d listings", len(indeed))
    except Exception as e:
        logger.exception("Indeed scrape failed: %s", e)

    # Hacker News (sync)
    try:
        hn = fetch_hn_listings()
        all_rows.extend(hn)
        logger.info("Hacker News: fetched %d listings", len(hn))
    except Exception as e:
        logger.exception("Hacker News scrape failed: %s", e)

    # AIJobs.net (sync)
    try:
        aijobs = fetch_aijobs_listings()
        all_rows.extend(aijobs)
        logger.info("AIJobs: fetched %d listings", len(aijobs))
    except Exception as e:
        logger.exception("AIJobs scrape failed: %s", e)

    # Hugging Face (sync)
    try:
        hf = fetch_huggingface_listings()
        all_rows.extend(hf)
        logger.info("Hugging Face: fetched %d listings", len(hf))
    except Exception as e:
        logger.exception("Hugging Face scrape failed: %s", e)

    # Y Combinator (sync)
    try:
        yc = fetch_ycombinator_listings()
        all_rows.extend(yc)
        logger.info("Y Combinator: fetched %d listings", len(yc))
    except Exception as e:
        logger.exception("Y Combinator scrape failed: %s", e)

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
