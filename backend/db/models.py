"""
SQLAlchemy models for Scout.
Listing model is used for job/internship listings from all sources.
Deduplication is done by apply_url (same URL = same listing).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Listing(Base):
    """
    Job or internship listing from any source (Remotive, We Work Remotely, etc.).
    apply_url is the canonical identifier for deduplication.
    """

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    remote: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    apply_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    date_posted: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    date_fetched: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # job | internship | null (unknown)
    listing_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)

    applications: Mapped[list["Application"]] = relationship("Application", back_populates="listing", lazy="select")

    def __repr__(self) -> str:
        return f"<Listing(id={self.id}, title={self.title!r}, company={self.company!r}, source={self.source})>"


class Resume(Base):
    """
    Parsed resume data (one row per user; latest upload overwrites or we keep history).
    skills, experience, preferred_roles stored as JSON strings for SQLite compatibility.
    """

    __tablename__ = "resume"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    skills: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array of strings
    experience: Mapped[str] = mapped_column(Text, default="", nullable=False)
    education: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preferred_roles: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Profile(Base):
    """
    User-provided profile: extra skills, about me, preferred roles. Merged with resume for scoring and cover letters.
    Single row (singleton); create on first PUT.
    """

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    custom_skills: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array
    about_me: Mapped[str] = mapped_column(Text, default="", nullable=False)
    preferred_roles: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON array
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Score(Base):
    """
    AI match score for a listing vs the user's resume. One score per listing (cached).
    """

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    skills_score: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_score: Mapped[int] = mapped_column(Integer, nullable=False)
    role_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CoverLetter(Base):
    """
    Generated or edited cover letter for a listing. Up to 3 versions per listing.
    """

    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    tone: Mapped[str] = mapped_column(String(50), default="Professional", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    edited_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Application(Base):
    """
    Tracks an application (or saved listing). One row per listing when user applies or saves.
    """

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="Applied", nullable=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    apply_method: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="applications")
