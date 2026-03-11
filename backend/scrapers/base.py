"""
Shared types for scrapers. All scrapers return a list of ListingRow dicts
with the same shape so the DB layer can insert into the listings table.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


def infer_listing_type(title: str, description: str) -> Optional[str]:
    """Infer 'internship' or 'job' from title and description text. Returns None if unclear."""
    text = (title + " " + (description or "")).lower()
    if "intern" in text or "internship" in text:
        return "internship"
    return "job"


def is_senior_role(title: str) -> bool:
    """Return True if the title suggests a senior, staff, or lead position."""
    t = title.lower()
    # Negative keywords that imply high experience
    senior_keywords = [
        "senior",
        "sr.",
        "sr ",
        "staff",
        "principal",
        "lead",
        "manager",
        "director",
        "vp",
        "architect",
        "expert",
        "head of",
        "chief",
        "senior scientist",
        "staff scientist",
    ]
    for kw in senior_keywords:
        if kw in t:
            return True
    return False


@dataclass
class ListingRow:
    """
    One job or internship listing as returned by any scraper. Maps directly to Listing model fields.
    listing_type: "job" | "internship" | None (unknown). remote: True for remote, False for on-site.
    date_fetched and created_at are set by the DB layer when inserting.
    """

    title: str
    company: str
    location: str
    remote: bool
    description: str
    apply_url: str
    source: str
    date_posted: Optional[datetime] = None
    listing_type: Optional[str] = None  # "job" | "internship"
