"""
Listing persistence and deduplication. Inserts scraper results into the listings table
only when apply_url is not already present; logs new vs duplicate counts.
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from .models import Listing

if TYPE_CHECKING:
    from scrapers.base import ListingRow

logger = logging.getLogger(__name__)


def insert_listings_deduplicated(db: Session, rows: list["ListingRow"]) -> tuple[int, int]:
    """
    Insert listing rows into the DB, skipping any whose apply_url already exists.
    Returns (inserted_count, duplicate_count). Caller should commit the session.
    """
    if not rows:
        return 0, 0

    now = datetime.now(timezone.utc)
    apply_urls = [r.apply_url for r in rows]

    existing_urls = {
        row[0]
        for row in db.query(Listing.apply_url).filter(Listing.apply_url.in_(apply_urls)).all()
    }

    to_insert = [r for r in rows if r.apply_url not in existing_urls]
    # Deduplicate within the batch (same URL can appear multiple times from scrapers)
    seen_in_batch: set[str] = set()
    to_insert_deduped: list["ListingRow"] = []
    for r in to_insert:
        url = (r.apply_url or "").strip()
        if not url or url in seen_in_batch:
            continue
        seen_in_batch.add(url)
        to_insert_deduped.append(r)
    to_insert = to_insert_deduped

    duplicate_count = len(rows) - len(to_insert)

    for r in to_insert:
        url = (r.apply_url or "").strip()
        listing = Listing(
            title=r.title,
            company=r.company,
            location=r.location,
            remote=r.remote,
            description=r.description,
            apply_url=url,
            source=r.source,
            date_posted=r.date_posted,
            date_fetched=now,
            created_at=now,
            listing_type=getattr(r, "listing_type", None),
        )
        db.add(listing)

    if to_insert or duplicate_count:
        logger.info(
            "Listings dedupe: inserted=%d, duplicate=%d (total from scrapers=%d)",
            len(to_insert),
            duplicate_count,
            len(rows),
        )
    return len(to_insert), duplicate_count
