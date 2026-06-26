"""
Orchestrates the full ingestion pipeline:
  uploaded file -> extract text -> detect components -> persist to Mongo

This is the single function the Streamlit upload page calls.
"""

import uuid
from typing import Union, BinaryIO

from app.db.mongo_client import get_db
from app.db.schemas import AnalysisRecord
from app.ingestion.extractors import extract_text
from app.ingestion.component_detector import detect_components
from app.models.enums import AnalysisStatus


def process_uploaded_file(filename: str, file: Union[str, BinaryIO]) -> AnalysisRecord:
    """
    Runs the ingestion pipeline for one uploaded file and saves the
    resulting AnalysisRecord to MongoDB's 'analyses' collection.

    Returns the saved AnalysisRecord (with its components populated).
    Raises ValueError if the file type is unsupported.
    """
    analysis_id = str(uuid.uuid4())

    try:
        raw_text = extract_text(filename, file)
        components = detect_components(raw_text)
        status = AnalysisStatus.ANALYZED.value
    except Exception:
        # Still record the failed attempt so it's visible in the DB,
        # but re-raise so the UI can show an error to the user.
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename=filename,
            raw_text=None,
            components=[],
            status=AnalysisStatus.FAILED.value,
        )
        get_db()["analyses"].insert_one(record.model_dump())
        raise

    record = AnalysisRecord(
        analysis_id=analysis_id,
        filename=filename,
        raw_text=raw_text,
        components=components,
        status=status,
    )

    get_db()["analyses"].insert_one(record.model_dump())
    return record


def get_analysis_by_id(analysis_id: str) -> AnalysisRecord | None:
    """Fetches a previously saved analysis by its analysis_id."""
    doc = get_db()["analyses"].find_one({"analysis_id": analysis_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return AnalysisRecord(**doc)