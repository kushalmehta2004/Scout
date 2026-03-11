"""
Hugging Face job listings scraper.
Uses the Hugging Face Workable API for job/internship discovery.
API: https://apply.workable.com/api/v1/widget/accounts/huggingface
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests

from .base import ListingRow, infer_listing_type, is_senior_role

SOURCE_NAME = "huggingface"
WORKABLE_URL = "https://apply.workable.com/api/v1/widget/accounts/huggingface"
logger = logging.getLogger(__name__)

def _job_to_listing_row(job: dict) -> Optional[ListingRow]:
    """Map one Workable job object to ListingRow."""
    title = (job.get("title") or "Untitled").strip()
    if is_senior_role(title):
        return None
        
    location = job.get("location", {}).get("name") or "Remote / Various"
    description = (job.get("description") or "").strip()
    listing_type = infer_listing_type(title, description)
    
    # Workable link format
    shortcode = job.get("shortcode")
    apply_url = f"https://apply.workable.com/huggingface/j/{shortcode}/" if shortcode else "https://huggingface.co/jobs"
    
    # Parse date posted
    published = job.get("published")
    date_posted = None
    if published:
        try:
            # Workable usually gives YYYY-MM-DD
            date_posted = datetime.fromisoformat(published).replace(tzinfo=timezone.utc)
        except:
            pass

    return ListingRow(
        title=title[:500],
        company="Hugging Face",
        location=location[:255],
        remote="remote" in location.lower() or "remote" in title.lower(),
        description=description,
        apply_url=apply_url,
        source=SOURCE_NAME,
        date_posted=date_posted,
        listing_type=listing_type,
    )

def fetch_huggingface_listings() -> List[ListingRow]:
    """Fetch all job listings from Hugging Face Workable board."""
    try:
        resp = requests.get(WORKABLE_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error("Hugging Face fetch failed: %s", e)
        return []

    jobs = data.get("jobs", [])
    if not isinstance(jobs, list):
        return []

    rows: list[ListingRow] = []
    for job in jobs:
        row = _job_to_listing_row(job)
        if row:
            rows.append(row)
            
    return rows
