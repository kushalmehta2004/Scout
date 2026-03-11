"""
Hacker News (Who is Hiring) scraper.
Uses the Algolia HN Search API to find the latest monthly hiring thread.
Threads are typically titled "Ask HN: Who is hiring? (January 2024)".
We only look at the current/most recent month's top-level comments.
"""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import requests

from .base import ListingRow, infer_listing_type, is_senior_role

SOURCE_NAME = "hacker_news"
logger = logging.getLogger(__name__)

# Search for the latest "Who is hiring" thread
SEARCH_URL = "https://hn.algolia.com/api/v1/search?query=Ask+HN:+Who+is+hiring&tags=story&numericFilters=created_at_i>%d"
# Get comments for a specific story
STORY_URL = "https://hn.algolia.com/api/v1/items/%s"

def _clean_html(text: str) -> str:
    """Very simple HTML tag removal for HN comments."""
    if not text:
        return ""
    # Replace <p> with newline, remove other tags
    text = text.replace("<p>", "\n").replace("</p>", "")
    return re.sub(r"<[^>]+>", "", text).strip()

def _parse_hn_comment(comment: dict) -> Optional[ListingRow]:
    """
    Parse a top-level comment from a 'Who is hiring' thread.
    Usually the first line is: Company | Title | Location | Options
    """
    text = comment.get("text")
    if not text:
        return None
    
    clean_text = _clean_html(text)
    lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
    if not lines:
        return None
    
    first_line = lines[0]
    # Filter out senior roles early
    if is_senior_role(first_line):
        return None
    
    # Try to extract company and title from first line
    # Common formats: "Company | Role | Location", "Company is hiring a Role", "Role at Company"
    parts = [p.strip() for p in first_line.split("|")]
    if len(parts) >= 2:
        company = parts[0]
        title = parts[1]
        location = parts[2] if len(parts) > 2 else "Unknown"
    else:
        # Fallback parsing
        company = "HN Startup"
        title = first_line[:100]
        location = "Remote / Unknown"

    # Infer type (internship vs job)
    listing_type = infer_listing_type(first_line, clean_text)
    
    # Check for remote
    remote = "remote" in first_line.lower() or "remote" in clean_text.lower()
    
    # Date posted
    created_at = comment.get("created_at")
    date_posted = None
    if created_at:
        try:
            date_posted = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except:
            pass

    return ListingRow(
        title=title[:500],
        company=company[:255],
        location=location[:255],
        remote=remote,
        description=clean_text,
        apply_url=f"https://news.ycombinator.com/item?id={comment.get('id')}",
        source=SOURCE_NAME,
        date_posted=date_posted,
        listing_type=listing_type,
    )

def fetch_hn_listings() -> List[ListingRow]:
    """
    Fetch job/internship listings from the latest Hacker News 'Who is hiring' thread.
    """
    # Look back 45 days to find the latest monthly thread
    threshold = int(datetime.now().timestamp()) - (45 * 24 * 3600)
    try:
        search_resp = requests.get(SEARCH_URL % threshold, timeout=20)
        search_resp.raise_for_status()
        hits = search_resp.json().get("hits", [])
    except Exception as e:
        logger.error("HN search failed: %s", e)
        return []

    # Find the most recent story with "Who is hiring?" in the title
    target_id = None
    for hit in hits:
        title = hit.get("title", "")
        if "Who is hiring?" in title and "Who is being hired?" not in title:
            target_id = hit.get("objectID")
            break
    
    if not target_id:
        logger.warning("No recent HN 'Who is hiring' thread found")
        return []

    try:
        story_resp = requests.get(STORY_URL % target_id, timeout=20)
        story_resp.raise_for_status()
        story_data = story_resp.json()
    except Exception as e:
        logger.error("HN story fetch failed for %s: %s", target_id, e)
        return []

    all_rows = []
    # Only process top-level comments (direct replies to the story)
    for comment in story_data.get("children", []):
        if not comment or comment.get("type") != "comment":
            continue
        row = _parse_hn_comment(comment)
        if row:
            all_rows.append(row)
            
    return all_rows
