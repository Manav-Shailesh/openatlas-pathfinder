"""
Phase 1 sanity test: confirms config loads and MongoDB read/write works.
Run with: pytest tests/test_db_connection.py -v
"""

from app.config import settings
from app.db.mongo_client import get_db, check_connection
from app.db.schemas import HealthCheckRecord


def test_settings_load():
    assert settings.MONGO_DB_NAME == "openatlas_pathfinder"
    assert settings.APP_NAME == "OpenATLAS Pathfinder"


def test_mongo_connection():
    assert check_connection() is True, (
        "Could not reach MongoDB. Is it running, and is MONGO_URI "
        "in your .env correct?"
    )


def test_mongo_write_and_read():
    db = get_db()
    collection = db["health_checks"]

    record = HealthCheckRecord(ok=True)
    inserted = collection.insert_one(record.model_dump())
    assert inserted.inserted_id is not None

    fetched = collection.find_one({"_id": inserted.inserted_id})
    assert fetched["ok"] is True

    # cleanup
    collection.delete_one({"_id": inserted.inserted_id})