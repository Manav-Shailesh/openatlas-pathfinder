"""
Single shared MongoDB connection for the whole app.
Import `get_db()` anywhere you need to read/write collections —
never instantiate MongoClient elsewhere.
"""

from functools import lru_cache
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Returns a cached MongoClient (created once per process)."""
    return MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)


@lru_cache(maxsize=1)
def get_db() -> Database:
    """Returns the application's MongoDB database handle."""
    client = get_client()
    return client[settings.MONGO_DB_NAME]


def check_connection() -> bool:
    """
    Pings the MongoDB server. Returns True if reachable, False otherwise.
    Used at app startup and in tests so failures are obvious early.
    """
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False