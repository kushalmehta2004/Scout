"""
RemoteOK job listings scraper. Uses the public API.
API: https://remoteok.com/api (returns array; first element is legal notice, rest are jobs).
All listings on RemoteOK are remote. We infer job vs internship from title/description.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from .base import ListingRow, infer_listing_type

REMOTEOK_API_URL = "https://remoteok.com/api"
SOURCE_NAME = "remoteok"
logger = logging.getLogger(__name__)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    try:
        s = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _job_to_listing_row(job: dict[str, Any]) -> ListingRow | None:
    """Map one RemoteOK API job object to ListingRow. Returns None if no valid apply URL."""
    job_id = job.get("id")
    if job_id is None:
        return None
    apply_url = f"https://remoteok.com/l/{job_id}"
    position = str(job.get("position") or job.get("title") or "Untitled").strip()[:500]
    company = str(job.get("company") or "Unknown").strip()[:255]
    description = str(job.get("description") or "").strip() or ""
    location = str(job.get("location") or "Remote").strip()[:255]
    listing_type = infer_listing_type(position, description)
    date_posted = _parse_date(job.get("date") or job.get("epoch"))
    if date_posted is None and job.get("epoch"):
        try:
            date_posted = datetime.fromtimestamp(int(job["epoch"]), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
    return ListingRow(
        title=position,
        company=company,
        location=location or "Remote",
        remote=True,
        description=description,
        apply_url=apply_url,
        source=SOURCE_NAME,
        date_posted=date_posted,
        listing_type=listing_type,
    )


def fetch_remoteok_listings() -> list[ListingRow]:
    """
    Fetch job listings from RemoteOK API. First element of response is legal/terms; we skip it.
    """
    try:
        resp = requests.get(REMOTEOK_API_URL, timeout=30, headers={"User-Agent": "Scout/1.0 (Job Discovery)"})
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.exception("RemoteOK request failed: %s", e)
        return []

    if not isinstance(data, list):
        return []

    rows: list[ListingRow] = []
    for i, item in enumerate(data):
        if i == 0 and isinstance(item, dict) and ("legal" in item or ("slug" not in item and "position" not in item)):
            continue
        if not isinstance(item, dict):
            continue
        row = _job_to_listing_row(item)
        if row is not None:
            rows.append(row)
    return rows
