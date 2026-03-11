"""
Indeed job listings via RSS. Indeed provides RSS feeds for search results.
URL format: https://rss.indeed.com/rss?q=QUERY&l=LOCATION
We use multiple preset queries (jobs remote, internships remote, etc.) so we get both jobs and internships.
"""

import logging
import os
from datetime import datetime, timezone
from time import mktime
from typing import Any
from urllib.parse import urlencode

import feedparser

from .base import ListingRow, infer_listing_type, is_senior_role

SOURCE_NAME = "indeed"
logger = logging.getLogger(__name__)

# Default RSS feeds: (query, location). Empty location = all locations.
# Users can override with INDEED_RSS_QUERIES (comma-separated "query|location" e.g. "software+engineer|remote,internship|")
DEFAULT_QUERIES = [
    ("junior software engineer remote", ""),
    ("entry level software engineer remote", ""),
    ("associate developer remote", ""),
    ("new grad software engineer remote", ""),
    ("internship software engineer remote", ""),
    ("internship remote", ""),
]


def _get_feed_urls() -> list[tuple[str, str]]:
    raw = os.getenv("INDEED_RSS_QUERIES", "").strip()
    if raw:
        pairs = []
        for part in raw.split(","):
            part = part.strip()
            if "|" in part:
                q, _, l = part.partition("|")
                pairs.append((q.strip(), l.strip()))
            else:
                pairs.append((part, ""))
        return pairs if pairs else DEFAULT_QUERIES
    return DEFAULT_QUERIES


def _build_rss_url(query: str, location: str) -> str:
    params = {"q": query}
    if location:
        params["l"] = location
    return "https://rss.indeed.com/rss?" + urlencode(params)


def _parse_date(entry: Any) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, key, None)
        if not parsed:
            continue
        try:
            ts = mktime(parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return None


def _entry_to_listing_row(entry: Any, query: str, location: str) -> ListingRow | None:
    link = (getattr(entry, "link", None) or "").strip()
    if not link:
        return None
    title_full = (getattr(entry, "title", None) or "Untitled").strip()
    description = (getattr(entry, "summary", None) or getattr(entry, "description", None) or "").strip()
    # Infer listing type from query and content
    q_lower = query.lower()
    if "intern" in q_lower:
        listing_type = "internship"
    else:
        listing_type = infer_listing_type(title_full, description)
    remote = "remote" in q_lower or "remote" in location.lower()
    return ListingRow(
        title=title_full[:500],
        company="Unknown",
        location=location or "Various",
        remote=remote,
        description=description,
        apply_url=link,
        source=SOURCE_NAME,
        date_posted=_parse_date(entry),
        listing_type=listing_type,
    )


def fetch_indeed_listings() -> list[ListingRow]:
    """
    Fetch job/internship listings from Indeed RSS feeds. Uses preset queries (remote jobs, internships, etc.).
    """
    all_rows: list[ListingRow] = []
    seen_urls: set[str] = set()

    for query, location in _get_feed_urls():
        if not query:
            continue
        url = _build_rss_url(query, location)
        try:
            parsed = feedparser.parse(
                url,
                request_headers={"User-Agent": "Scout/1.0 (Job Discovery; https://github.com/scout)"},
            )
        except Exception as e:
            logger.warning("Indeed RSS fetch failed for %s: %s", url, e)
            continue
        for entry in getattr(parsed, "entries", []) or []:
            title = (getattr(entry, "title", None) or "").strip()
            if is_senior_role(title):
                continue
            row = _entry_to_listing_row(entry, query, location)
            if row is not None and row.apply_url and row.apply_url not in seen_urls:
                seen_urls.add(row.apply_url)
                all_rows.append(row)
    return all_rows
