"""
Database connection and session management for Scout.
Uses SQLite by default; engine and sessions are created here.
Tables are created on init (call init_db() at app startup).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from .models import Base

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they do not exist. Call once at app startup."""
    Base.metadata.create_all(bind=engine)
    # Add follow_up_date to applications if missing (Phase 6 migration)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT 1 FROM pragma_table_info('applications') WHERE name='follow_up_date'"))
        if r.fetchone() is None:
            conn.execute(text("ALTER TABLE applications ADD COLUMN follow_up_date DATETIME"))
            conn.commit()
    # Add listing_type to listings if missing (multi-source + jobs/internships)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT 1 FROM pragma_table_info('listings') WHERE name='listing_type'"))
        if r.fetchone() is None:
            conn.execute(text("ALTER TABLE listings ADD COLUMN listing_type VARCHAR(20)"))
            conn.commit()


def get_db():
    """
    Dependency that yields a DB session. Use in FastAPI with Depends(get_db).
    Ensures session is closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
