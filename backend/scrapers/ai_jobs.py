"""
AIJobs.net job listings scraper.
Uses the AIJobs.net RSS feed for job/internship discovery.
Feed: https://aijobs.net/feed/rss/
"""

import logging
from datetime import datetime, timezone
from time import mktime
from typing import List, Optional

import feedparser

from .base import ListingRow, infer_listing_type, is_senior_role

SOURCE_NAME = "ai_jobs"
RSS_URL = "https://aijobs.net/feed/rss/"
logger = logging.getLogger(__name__)

def _parse_date(entry) -> Optional[datetime]:
    """Parse RSS entry date."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, key, None)
        if not parsed:
            continue
        try:
            ts = mktime(parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except:
            pass
    return None

def _entry_to_listing_row(entry) -> Optional[ListingRow]:
    """Map RSS entry to ListingRow."""
    link = (getattr(entry, "link", None) or "").strip()
    if not link:
        return None
    
    title_full = (getattr(entry, "title", None) or "Untitled").strip()
    # Filter out senior roles
    if is_senior_role(title_full):
        return None
        
    description = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "").strip()
    
    # AIJobs.net usually includes company and location in the title or content
    # For now, we take title as-is and infer listing type
    listing_type = infer_listing_type(title_full, description)
    
    # Check for remote
    remote = "remote" in title_full.lower() or "remote" in description.lower()
    
    return ListingRow(
        title=title_full[:500],
        company="AIJobs.net Company",
        location="Remote / Various",
        remote=remote,
        description=description,
        apply_url=link,
        source=SOURCE_NAME,
        date_posted=_parse_date(entry),
        listing_type=listing_type,
    )

def fetch_aijobs_listings() -> List[ListingRow]:
    """Fetch AI/ML job listings from AIJobs.net RSS feed."""
    try:
        parsed = feedparser.parse(RSS_URL)
    except Exception as e:
        logger.error("AIJobs.net fetch failed: %s", e)
        return []

    all_rows = []
    for entry in getattr(parsed, "entries", []) or []:
        row = _entry_to_listing_row(entry)
        if row:
            all_rows.append(row)
            
    return all_rows
