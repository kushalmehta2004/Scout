"""
We Work Remotely job listings scraper. Uses the public RSS feed.
Feed: https://weworkremotely.com/remote-jobs.rss
"""

from datetime import datetime, timezone
from typing import Any

import feedparser

from .base import ListingRow, infer_listing_type

WWR_RSS_URL = "https://weworkremotely.com/remote-jobs.rss"
SOURCE_NAME = "we_work_remotely"


def _parse_date(entry: Any) -> datetime | None:
    """Parse RSS entry published/updated date to timezone-aware datetime."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, key, None)
        if not parsed:
            continue
        try:
            # feedparser returns time.struct_time in UTC
            from time import mktime
            ts = mktime(parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return None


def _entry_to_listing_row(entry: Any) -> ListingRow | None:
    """Map one RSS entry to ListingRow. Returns None if link is missing."""
    link = (getattr(entry, "link", None) or "").strip()
    if not link:
        return None

    title_full = (getattr(entry, "title", None) or "Untitled").strip()
    # WWR often uses "Job Title at Company" or "Company: Job Title"
    if " at " in title_full:
        parts = title_full.split(" at ", 1)
        title = parts[0].strip()[:500]
        company = parts[1].strip()[:255] if len(parts) > 1 else "Unknown"
    elif ": " in title_full:
        parts = title_full.split(": ", 1)
        company = (parts[0].strip())[:255]
        title = (parts[1].strip())[:500] if len(parts) > 1 else title_full[:500]
    else:
        title = title_full[:500]
        company = "Unknown"

    description = (getattr(entry, "description", None) or getattr(entry, "summary", None) or "").strip()

    listing_type = infer_listing_type(title_full, description)
    return ListingRow(
        title=title or "Untitled",
        company=company or "Unknown",
        location="Remote",
        remote=True,
        description=description,
        apply_url=link,
        source=SOURCE_NAME,
        date_posted=_parse_date(entry),
        listing_type=listing_type,
    )


def fetch_weworkremotely_listings() -> list[ListingRow]:
    """
    Fetch job listings from We Work Remotely RSS feed. Returns a list of ListingRow.
    Uses feedparser (sync). Raises on network errors; caller should catch and log.
    """
    parsed = feedparser.parse(WWR_RSS_URL)

    rows: list[ListingRow] = []
    for entry in getattr(parsed, "entries", []) or []:
        row = _entry_to_listing_row(entry)
        if row is not None:
            rows.append(row)

    return rows
