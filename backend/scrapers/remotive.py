"""
Remotive job listings scraper. Uses the public JSON API.
API docs: https://remotive.com/api/remote-jobs (returns jobs array).
"""

from datetime import datetime, timezone
from typing import Any

import aiohttp

from .base import ListingRow, infer_listing_type, is_senior_role

REMOTIVE_JOBS_URL = "https://remotive.com/api/remote-jobs"
SOURCE_NAME = "remotive"


def _parse_date(value: Any) -> datetime | None:
    """Parse ISO date string to timezone-aware datetime, or return None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _job_to_listing_row(job: dict[str, Any]) -> ListingRow:
    """Map one Remotive API job object to ListingRow."""
    title = str(job.get("title") or "Untitled").strip()[:500]
    desc = str(job.get("description") or "").strip() or ""
    job_type = (job.get("job_type") or "").strip().lower()
    listing_type = "internship" if job_type == "internship" else infer_listing_type(title, desc)
    return ListingRow(
        title=title,
        company=str(job.get("company_name") or job.get("company") or "Unknown").strip()[:255],
        location=str(job.get("location") or job.get("candidate_required_location") or "Remote").strip()[:255],
        remote=True,
        description=desc,
        apply_url=str(job.get("url") or job.get("apply_url") or "").strip(),
        source=SOURCE_NAME,
        date_posted=_parse_date(job.get("published_at") or job.get("published_date")),
        listing_type=listing_type,
    )


async def fetch_remotive_listings() -> list[ListingRow]:
    """
    Fetch all job listings from Remotive API. Returns a list of ListingRow.
    Raises on network errors; caller should catch and log.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(REMOTIVE_JOBS_URL) as resp:
            resp.raise_for_status()
            data = await resp.json()

    jobs = data.get("jobs") or data
    if not isinstance(jobs, list):
        return []

    rows: list[ListingRow] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = str(job.get("title") or "").strip()
        if is_senior_role(title):
            continue
        apply_url = str(job.get("url") or job.get("apply_url") or "").strip()
        if not apply_url:
            continue
        rows.append(_job_to_listing_row(job))

    return rows
