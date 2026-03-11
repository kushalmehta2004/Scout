"""
Y Combinator (Work at a Startup) scraper.
Uses the Algolia public search API for startups.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests

from .base import ListingRow, infer_listing_type, is_senior_role

SOURCE_NAME = "ycombinator"
# Correct Algolia credentials for YC Work at a Startup
ALGOLIA_APP_ID = "45BWUJ1YL5"
ALGOLIA_API_KEY = "b03657cd3551528c11545ef0c8a5a41a"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/JobListing_production/query"
logger = logging.getLogger(__name__)

def _job_to_listing_row(job: dict) -> Optional[ListingRow]:
    """Map one Y Combinator Algolia job hit to ListingRow."""
    title = (job.get("title") or "Untitled").strip()
    if is_senior_role(title):
        return None
        
    company = (job.get("companyName") or "Startup").strip()
    description = (job.get("description") or "").strip()
    location = (job.get("location") or "Remote / Various").strip()
    listing_type = infer_listing_type(title, description)
    
    # Check for remote
    remote = "remote" in location.lower() or "remote" in title.lower() or "remote" in description.lower()
    
    # Create absolute link to the job listing
    apply_url = f"https://www.workatastartup.com/jobs/{job.get('objectID')}"
    
    # Parse date posted (usually provided as an integer unix timestamp)
    created_at = job.get("createdAt")
    date_posted = None
    if created_at:
        try:
            date_posted = datetime.fromtimestamp(int(created_at), tz=timezone.utc)
        except:
            pass

    return ListingRow(
        title=title[:500],
        company=company[:255],
        location=location[:255],
        remote=remote,
        description=description,
        apply_url=apply_url,
        source=SOURCE_NAME,
        date_posted=date_posted,
        listing_type=listing_type,
    )

def fetch_ycombinator_listings() -> List[ListingRow]:
    """Fetch all job listings from Y Combinator's Algolia index."""
    try:
        # Search for jobs, looking for recent ones
        payload = {
            "query": "",
            "params": "hitsPerPage=100&filters=status:active"
        }
        headers = {
            "x-algolia-api-key": ALGOLIA_API_KEY,
            "x-algolia-application-id": ALGOLIA_APP_ID
        }
        resp = requests.post(ALGOLIA_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("Y Combinator fetch failed: %s", e)
        return []

    hits = data.get("hits", [])
    if not isinstance(hits, list):
        return []

    rows: list[ListingRow] = []
    for hit in hits:
        row = _job_to_listing_row(hit)
        if row:
            rows.append(row)
            
    return rows
