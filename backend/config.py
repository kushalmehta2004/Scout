"""
Application configuration. Loads from environment variables.
Use python-dotenv so .env is loaded when this module is imported.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Database: use DATABASE_URL if set, else build from SQLITE_PATH, else default
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sqlite_path = os.getenv("SQLITE_PATH", "./data/scout.db")
    # SQLite URLs use forward slashes; relative path is fine for default
    DATABASE_URL = "sqlite:///" + sqlite_path.replace("\\", "/")
