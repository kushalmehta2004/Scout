# Job & internship sources

Scout pulls listings from multiple public sources. Each listing is tagged as **job** or **internship** when we can detect it, and as **remote** or **on-site** based on the source or listing text.

## Supported sources

| Source | Type | Remote / on-site | Notes |
|--------|------|------------------|--------|
| **Remotive** | Jobs + internships | Remote only | Public API; we infer internship from `job_type` or title/description. |
| **We Work Remotely** | Jobs + internships | Remote only | RSS feed; we infer internship from title/description. |
| **RemoteOK** | Jobs + internships | Remote only | Public API; we infer internship from title/description. |
| **Indeed** | Jobs + internships | Depends on query | RSS feeds; we use preset queries (e.g. "software engineer remote", "internship remote"). Configurable via `INDEED_RSS_QUERIES`. |

## Why LinkedIn is not included

**LinkedIn does not offer a public API** for job search that we can use. Their official products (e.g. LinkedIn Talent Solutions) are for recruiters/enterprise and are not suitable for this app. **Scraping LinkedIn is against their Terms of Service** and they actively block automated access. We therefore do not implement LinkedIn as a source.

To use LinkedIn, use linkedin.com directly; you can still save and track applications from other sources in Scout.

## Adding more sources

To add a new source:

1. Implement a scraper in `backend/scrapers/` that returns a list of `ListingRow` (see `scrapers/base.py`).
2. Set `listing_type` to `"job"` or `"internship"` when known (use `infer_listing_type(title, description)` for heuristics).
3. Set `remote` to `True` or `False` based on the listing.
4. Register the fetcher in `scheduler.run_scrape_job()` and add the source to the frontend filter dropdown.

## Environment variables

- **INDEED_RSS_QUERIES** (optional): Comma-separated `query|location` pairs for Indeed RSS. Example: `software+engineer+remote|,internship|remote`. Defaults to a set of common remote and internship queries.
