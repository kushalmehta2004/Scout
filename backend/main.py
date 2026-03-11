"""
Scout backend — FastAPI app. Job listing scrape API and (later) listings, resume, apply.
"""

import json
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from typing import Optional

from pydantic import BaseModel
from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, nulls_last
from sqlalchemy.orm import Session, joinedload

from ai.cover_letter import generate_cover_letter
from ai.matcher import score_listing
from db.database import get_db, init_db
from db.models import Application, CoverLetter, Listing, Profile, Resume, Score
from applier.dispatcher import run_apply as dispatch_apply
from resume.parser import parse_resume
from scheduler import run_scrape_job, start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables, start scheduler, run initial scrape in background."""
    init_db()
    start_scheduler()
    # Run one scrape in background so listings appear without manual trigger
    def run_initial_scrape():
        try:
            run_scrape_job()
        except Exception as e:
            logger.exception("Initial scrape failed: %s", e)

    threading.Thread(target=run_initial_scrape, daemon=True).start()
    yield
    stop_scheduler()


app = FastAPI(title="Scout", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _listing_to_dict(row: Listing, score_row: Optional[Score] = None) -> dict:
    """Serialize a Listing model row to a JSON-friendly dict; optionally include score."""
    out = {
        "id": row.id,
        "title": row.title,
        "company": row.company,
        "location": row.location,
        "remote": row.remote,
        "description": row.description,
        "apply_url": row.apply_url,
        "source": row.source,
        "date_posted": row.date_posted.isoformat() if row.date_posted else None,
        "date_fetched": row.date_fetched.isoformat(),
        "created_at": row.created_at.isoformat(),
        "listing_type": getattr(row, "listing_type", None),
    }
    if score_row is not None:
        out["score"] = {
            "overall_score": score_row.overall_score,
            "reasoning": score_row.reasoning,
            "scored_at": score_row.scored_at.isoformat(),
        }
    else:
        out["score"] = None
    return out


@app.get("/api/listings")
def get_listings(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = Query("date", description="date | company | score"),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    remote: Optional[bool] = Query(None),
    source: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None, description="job | internship"),
):
    """
    Return listings with pagination, filters (score range, remote, source, listing_type), and sort.
    Each item includes optional score when available.
    """
    q = db.query(Listing, Score).outerjoin(Score, Listing.id == Score.listing_id)

    if min_score is not None or max_score is not None:
        if min_score is not None and max_score is not None:
            q = q.filter(and_(Score.overall_score >= min_score, Score.overall_score <= max_score))
        elif min_score is not None:
            q = q.filter(Score.overall_score >= min_score)
        else:
            q = q.filter(Score.overall_score <= max_score)
    if remote is not None:
        q = q.filter(Listing.remote == remote)
    if source is not None and source.strip():
        q = q.filter(Listing.source == source.strip())
    if listing_type is not None and listing_type.strip():
        q = q.filter(Listing.listing_type == listing_type.strip())

    total = q.count()

    if sort == "company":
        q = q.order_by(Listing.company.asc(), Listing.created_at.desc())
    elif sort == "score":
        q = q.order_by(nulls_last(Score.overall_score.desc()), Listing.created_at.desc())
    else:
        q = q.order_by(Listing.created_at.desc())

    rows = q.offset(offset).limit(limit).all()
    # With outerjoin, rows are (Listing, Score | None)
    items = []
    for row in rows:
        listing = row[0] if isinstance(row, tuple) else row
        score_row = row[1] if isinstance(row, tuple) and len(row) > 1 else None
        items.append(_listing_to_dict(listing, score_row))

    return {"total": total, "items": items}


@app.post("/api/listings/scrape")
def trigger_scrape():
    """
    Run the scrape job once (Remotive + We Work Remotely), dedupe and insert.
    Returns counts of inserted and duplicate listings.
    """
    inserted, duplicates = run_scrape_job()
    return {"inserted": inserted, "duplicates": duplicates}


def _resume_to_dict(row: Resume) -> dict:
    """Serialize Resume model to JSON-friendly dict (skills/preferred_roles as lists)."""
    return {
        "id": row.id,
        "raw_text": row.raw_text,
        "skills": json.loads(row.skills) if row.skills else [],
        "experience": row.experience,
        "education": row.education,
        "preferred_roles": json.loads(row.preferred_roles) if row.preferred_roles else [],
        "updated_at": row.updated_at.isoformat(),
    }


@app.post("/api/resume/upload")
def upload_resume(file: UploadFile, db: Session = Depends(get_db)):
    """
    Upload a resume (PDF or DOCX). Parses and stores structured data; overwrites previous resume.
    """
    if not file.filename:
        return {"ok": False, "error": "Missing filename"}
    fn = file.filename.lower()
    if not (fn.endswith(".pdf") or fn.endswith(".docx") or fn.endswith(".doc")):
        return {"ok": False, "error": "Only PDF and DOCX are supported"}

    content = file.file.read()
    if not content:
        return {"ok": False, "error": "Empty file"}

    try:
        data = parse_resume(content, file.filename or "")
    except Exception as e:
        logger.exception("Resume parse failed: %s", e)
        return {"ok": False, "error": f"Parse failed: {e!s}"}

    now = datetime.now(timezone.utc)
    resume = db.query(Resume).order_by(Resume.updated_at.desc()).first()
    if resume is None:
        resume = Resume(
            raw_text="",
            skills="[]",
            experience="",
            education="",
            preferred_roles="[]",
            updated_at=now,
        )
        db.add(resume)

    resume.raw_text = data["raw_text"]
    resume.skills = json.dumps(data["skills"])
    resume.experience = data["experience"]
    resume.education = data["education"]
    resume.preferred_roles = json.dumps(data["preferred_roles"])
    resume.updated_at = now
    db.commit()
    db.refresh(resume)
    return {"ok": True, "resume": _resume_to_dict(resume)}


@app.get("/api/resume")
def get_resume(db: Session = Depends(get_db)):
    """Return the latest uploaded resume (parsed data). 404 if none."""
    resume = db.query(Resume).order_by(Resume.updated_at.desc()).first()
    if resume is None:
        return {"resume": None}
    return {"resume": _resume_to_dict(resume)}


# ---- Profile (skills, about me — merged with resume for scoring) ----

def _profile_to_dict(row: Profile) -> dict:
    return {
        "id": row.id,
        "custom_skills": json.loads(row.custom_skills) if row.custom_skills else [],
        "about_me": row.about_me or "",
        "preferred_roles": json.loads(row.preferred_roles) if row.preferred_roles else [],
        "updated_at": row.updated_at.isoformat(),
    }


def _build_combined_summary(resume: Resume | None, profile: Profile | None) -> str:
    """Build candidate summary from resume + profile for scoring and cover letters."""
    parts = []
    if resume:
        if resume.raw_text:
            parts.append("Resume (excerpt):\n" + resume.raw_text[:4000].strip())
        if resume.skills and resume.skills != "[]":
            parts.append("Skills (from resume): " + resume.skills[:1500])
        if resume.experience:
            parts.append("Experience:\n" + resume.experience[:2000].strip())
        if resume.education:
            parts.append("Education:\n" + resume.education[:1000].strip())
        if resume.preferred_roles and resume.preferred_roles != "[]":
            parts.append("Preferred roles (from resume): " + resume.preferred_roles[:500])
    if profile:
        if profile.custom_skills and profile.custom_skills != "[]":
            parts.append("Additional skills (user-provided): " + profile.custom_skills[:1500])
        if (profile.about_me or "").strip():
            parts.append("About me / additional info:\n" + (profile.about_me or "").strip()[:3000])
        if profile.preferred_roles and profile.preferred_roles != "[]":
            parts.append("Preferred roles (user-provided): " + profile.preferred_roles[:500])
    return "\n\n".join(parts) if parts else "No resume or profile content provided."


@app.get("/api/profile")
def get_profile(db: Session = Depends(get_db)):
    """Return user profile (custom skills, about me, preferred roles). Empty defaults if none."""
    profile = db.query(Profile).first()
    if profile is None:
        return {
            "profile": {
                "id": 0,
                "custom_skills": [],
                "about_me": "",
                "preferred_roles": [],
                "updated_at": None,
            },
        }
    return {"profile": _profile_to_dict(profile)}


class ProfileUpdateBody(BaseModel):
    custom_skills: Optional[list[str]] = None
    about_me: Optional[str] = None
    preferred_roles: Optional[list[str]] = None


@app.put("/api/profile")
def update_profile(body: ProfileUpdateBody, db: Session = Depends(get_db)):
    """Create or update user profile. Used together with resume for scoring and cover letters."""
    now = datetime.now(timezone.utc)
    profile = db.query(Profile).first()
    if profile is None:
        profile = Profile(
            custom_skills="[]",
            about_me="",
            preferred_roles="[]",
            updated_at=now,
        )
        db.add(profile)
        db.flush()
    if body.custom_skills is not None:
        profile.custom_skills = json.dumps(body.custom_skills)
    if body.about_me is not None:
        profile.about_me = body.about_me
    if body.preferred_roles is not None:
        profile.preferred_roles = json.dumps(body.preferred_roles)
    profile.updated_at = now
    db.commit()
    db.refresh(profile)
    return {"ok": True, "profile": _profile_to_dict(profile)}


def _score_to_dict(row: Score) -> dict:
    """Serialize Score model to JSON."""
    return {
        "listing_id": row.listing_id,
        "overall_score": row.overall_score,
        "skills_score": row.skills_score,
        "experience_score": row.experience_score,
        "role_score": row.role_score,
        "reasoning": row.reasoning,
        "scored_at": row.scored_at.isoformat(),
    }


@app.get("/api/scores/{listing_id}")
def get_listing_score(
    listing_id: int,
    refresh: bool = Query(False, description="If true, recompute score even when cached (e.g. to fix 0 or stale scores)."),
    db: Session = Depends(get_db),
):
    """
    Return match score for a listing vs the user's resume. Computes and caches if not present.
    Requires a resume to be uploaded first; requires GROQ_API_KEY for first-time scoring.
    Use ?refresh=true to recompute and replace a cached score.
    """
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(
            status_code=404,
            detail="Listing not found. Use GET /api/listings to see available listing IDs, or run POST /api/listings/scrape to fetch jobs.",
        )

    existing = db.query(Score).filter(Score.listing_id == listing_id).first()
    if existing is not None and not refresh:
        return {"score": _score_to_dict(existing)}
    if existing is not None and refresh:
        db.delete(existing)
        db.commit()

    resume = db.query(Resume).order_by(Resume.updated_at.desc()).first()
    profile = db.query(Profile).first()
    combined = _build_combined_summary(resume, profile)
    if not combined or combined.strip() == "No resume or profile content provided.":
        raise HTTPException(
            status_code=400,
            detail="Upload a resume and/or add your profile (skills, about me) first",
        )

    try:
        result = score_listing(
            resume_summary=combined,
            job_title=listing.title,
            company=listing.company,
            job_description=listing.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Score API failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e!s}")

    now = datetime.now(timezone.utc)
    score_row = Score(
        listing_id=listing_id,
        overall_score=result["overall"],
        skills_score=result["skills_match"],
        experience_score=result["experience_match"],
        role_score=result["role_match"],
        reasoning=result["reasoning"],
        scored_at=now,
    )
    db.add(score_row)
    db.commit()
    db.refresh(score_row)
    return {"score": _score_to_dict(score_row)}


def _cover_letter_to_dict(row: CoverLetter) -> dict:
    """Serialize CoverLetter to JSON."""
    return {
        "id": row.id,
        "listing_id": row.listing_id,
        "content": row.content,
        "version": row.version,
        "tone": row.tone,
        "generated_at": row.generated_at.isoformat(),
        "edited_by_user": row.edited_by_user,
    }


@app.get("/api/listings/{listing_id}")
def get_listing_detail(listing_id: int, db: Session = Depends(get_db)):
    """Return a single listing with score and cover letters (up to 3 versions)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    score_row = db.query(Score).filter(Score.listing_id == listing_id).first()
    letters = (
        db.query(CoverLetter)
        .filter(CoverLetter.listing_id == listing_id)
        .order_by(CoverLetter.generated_at.desc())
        .limit(3)
        .all()
    )

    out = _listing_to_dict(listing, score_row)
    out["cover_letters"] = [_cover_letter_to_dict(c) for c in letters]
    return out


@app.post("/api/cover-letter/generate")
def generate_cover_letter_for_listing(
    db: Session = Depends(get_db),
    listing_id: int = Query(..., description="Listing ID"),
    tone: str = Query("Professional", description="Professional | Conversational | Technical | Enthusiastic"),
):
    """Generate a cover letter for a listing via Gemini. Keeps max 3 versions; creates new or rotates oldest."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    resume = db.query(Resume).order_by(Resume.updated_at.desc()).first()
    profile = db.query(Profile).first()
    combined = _build_combined_summary(resume, profile)
    if not combined or combined.strip() == "No resume or profile content provided.":
        raise HTTPException(
            status_code=400,
            detail="Upload a resume and/or add your profile (skills, about me) first",
        )
    try:
        content = generate_cover_letter(
            resume_summary=combined,
            job_title=listing.title,
            company=listing.company,
            job_description=listing.description,
            tone=tone.strip() or "Professional",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Cover letter generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Generation failed: {e!s}")

    now = datetime.now(timezone.utc)
    existing = (
        db.query(CoverLetter)
        .filter(CoverLetter.listing_id == listing_id)
        .order_by(CoverLetter.generated_at.asc())
        .all()
    )
    if len(existing) >= 3:
        db.delete(existing[0])
        existing = existing[1:]
    next_version = max((c.version for c in existing), default=0) + 1
    letter = CoverLetter(
        listing_id=listing_id,
        content=content,
        version=next_version,
        tone=tone.strip() or "Professional",
        generated_at=now,
        edited_by_user=False,
    )
    db.add(letter)
    db.commit()
    db.refresh(letter)
    return {"ok": True, "cover_letter": _cover_letter_to_dict(letter)}


class CoverLetterUpdateBody(BaseModel):
    content: str


@app.put("/api/cover-letter/{letter_id}")
def update_cover_letter(
    letter_id: int,
    body: CoverLetterUpdateBody,
    db: Session = Depends(get_db),
):
    """Update a cover letter's content and mark as edited by user."""
    letter = db.query(CoverLetter).filter(CoverLetter.id == letter_id).first()
    if letter is None:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    letter.content = body.content
    letter.edited_by_user = True
    db.commit()
    db.refresh(letter)
    return {"ok": True, "cover_letter": _cover_letter_to_dict(letter)}


class ApplyConfirmBody(BaseModel):
    confirm: bool = False


@app.post("/api/apply/{listing_id}")
def apply_to_listing(
    listing_id: int,
    body: ApplyConfirmBody,
    db: Session = Depends(get_db),
):
    """
    Try to apply to the listing (fill form via Playwright or return manual fallback).
    Requires body { "confirm": true } for human-in-the-loop. Returns apply_url and
    cover_letter_text for manual fallback (open URL + copy to clipboard).
    """
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true in request body to apply.")

    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    cover_letter_text = ""
    letter = (
        db.query(CoverLetter)
        .filter(CoverLetter.listing_id == listing_id)
        .order_by(CoverLetter.generated_at.desc())
        .first()
    )
    if letter:
        cover_letter_text = letter.content

    result = dispatch_apply(apply_url=listing.apply_url, cover_letter_text=cover_letter_text)

    now = datetime.now(timezone.utc)
    app = db.query(Application).filter(Application.listing_id == listing_id).first()
    if app is None:
        app = Application(
            listing_id=listing_id,
            status="Applied",
            applied_at=now,
            apply_method=result.method,
            notes="",
        )
        db.add(app)
    else:
        app.status = "Applied"
        app.applied_at = app.applied_at or now
        app.apply_method = result.method
    db.commit()
    db.refresh(app)

    return {
        "ok": result.ok,
        "method": result.method,
        "message": result.message,
        "apply_url": result.apply_url,
        "cover_letter_text": result.cover_letter_text,
    }


# ---- Phase 6: Application Tracker ----

def _application_to_dict(app: Application, listing: Listing) -> dict:
    return {
        "id": app.id,
        "listing_id": app.listing_id,
        "listing_title": listing.title,
        "listing_company": listing.company,
        "apply_url": listing.apply_url,
        "status": app.status,
        "applied_at": app.applied_at.isoformat() if app.applied_at else None,
        "apply_method": app.apply_method,
        "notes": app.notes or "",
        "follow_up_date": app.follow_up_date.isoformat() if app.follow_up_date else None,
    }


@app.get("/api/applications")
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    sort: str = Query("applied_at", description="Sort by: applied_at, status, company"),
    db: Session = Depends(get_db),
):
    """Return all applications with listing summary; optional filter by status, sort."""
    q = db.query(Application).options(joinedload(Application.listing)).join(Listing, Application.listing_id == Listing.id)
    if status is not None and status != "":
        q = q.filter(Application.status == status)
    if sort == "company":
        q = q.order_by(Listing.company)
    elif sort == "status":
        q = q.order_by(Application.status)
    else:
        q = q.order_by(nulls_last(Application.applied_at.desc()))
    rows = q.all()
    applications = [_application_to_dict(app, app.listing) for app in rows]
    return {"items": applications, "total": len(applications)}


class ApplicationUpdateBody(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None  # ISO date or null


@app.put("/api/applications/{app_id}")
def update_application(
    app_id: int,
    body: ApplicationUpdateBody,
    db: Session = Depends(get_db),
):
    """Update application status, notes, or follow_up_date."""
    app = db.query(Application).filter(Application.id == app_id).first()
    if app is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if body.status is not None:
        app.status = body.status
    if body.notes is not None:
        app.notes = body.notes
    if body.follow_up_date is not None:
        if body.follow_up_date == "":
            app.follow_up_date = None
        else:
            try:
                app.follow_up_date = datetime.fromisoformat(body.follow_up_date.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                app.follow_up_date = None
    db.commit()
    db.refresh(app)
    listing = db.query(Listing).filter(Listing.id == app.listing_id).first()
    return _application_to_dict(app, listing)


class SaveForLaterBody(BaseModel):
    listing_id: int


@app.post("/api/applications/save")
def save_listing_for_later(body: SaveForLaterBody, db: Session = Depends(get_db)):
    """Create an application with status Saved for the given listing (idempotent)."""
    listing = db.query(Listing).filter(Listing.id == body.listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    app = db.query(Application).filter(Application.listing_id == body.listing_id).first()
    if app is not None:
        return _application_to_dict(app, listing)
    app = Application(
        listing_id=body.listing_id,
        status="Saved",
        applied_at=None,
        apply_method="manual",
        notes="",
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return _application_to_dict(app, listing)


@app.get("/api/applications/export")
def export_applications_csv(
    format: str = Query("csv", description="Export format (csv)"),
    db: Session = Depends(get_db),
):
    """Export applications as CSV. Returns file attachment."""
    if format != "csv":
        raise HTTPException(status_code=400, detail="Only format=csv is supported")
    q = db.query(Application).options(joinedload(Application.listing)).order_by(nulls_last(Application.applied_at.desc()))
    rows = q.all()
    import csv
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "company", "status", "applied_at", "apply_method", "notes", "follow_up_date"])
    for app in rows:
        listing = app.listing
        if not listing:
            continue
        writer.writerow([
            listing.title,
            listing.company,
            app.status,
            app.applied_at.isoformat() if app.applied_at else "",
            app.apply_method,
            app.notes or "",
            app.follow_up_date.strftime("%Y-%m-%d") if app.follow_up_date else "",
        ])
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )
