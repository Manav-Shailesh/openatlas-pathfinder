"""
Central configuration for OpenATLAS Pathfinder.
All other modules should import settings from here instead of
reading environment variables directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables


class Settings:
    # --- MongoDB ---
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "openatlas_pathfinder")

    # --- App ---
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_NAME: str = "OpenATLAS Pathfinder"

    # --- Risk scoring thresholds (used in Phase 6) ---
    RISK_LOW_MAX: int = 30
    RISK_MEDIUM_MAX: int = 60
    # anything above RISK_MEDIUM_MAX is High

    # --- File upload limits (used in Phase 2) ---
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: tuple = (".pdf", ".txt", ".md")


settings = Settings()