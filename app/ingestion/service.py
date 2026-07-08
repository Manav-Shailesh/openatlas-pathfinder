"""
Orchestrates the full ingestion pipeline:
  uploaded file -> extract (text or diagram) -> detect components -> persist to Mongo

Text files (.pdf / .txt / .md) -> text extraction + keyword detection
Image files (.png / .jpg / .jpeg) -> Gemini Vision diagram understanding

Both paths produce the same ArchitectureComponent structure so Phases
3-8 never need to know which path was taken.
"""

import uuid
import os
from typing import Union, BinaryIO

from app.db.mongo_client import get_db
from app.db.schemas import AnalysisRecord
from app.ingestion.extractors import extract_text
from app.ingestion.component_detector import detect_components
from app.ingestion.diagram_extractor import extract_components_from_diagram
from app.models.enums import AnalysisStatus

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
_TEXT_EXTENSIONS  = (".pdf", ".txt", ".md")

print(f"[service.py] module loaded — image extensions: {_IMAGE_EXTENSIONS}")


def _classify_file(filename: str) -> str:
    """
    Returns 'image', 'text', or raises ValueError for unknown types.
    Uses only the file extension — never trusts MIME type from Streamlit
    because Streamlit's UploadedFile MIME detection is unreliable for
    some PNG files and reports them as application/octet-stream.
    """
    # Strip any path components — only look at the bare filename
    name = os.path.basename(filename).lower().strip()

    print(f"[service.py] _classify_file called with: {name!r}")

    if name.endswith(_IMAGE_EXTENSIONS):
        print(f"[service.py] classified as IMAGE")
        return "image"
    elif name.endswith(_TEXT_EXTENSIONS):
        print(f"[service.py] classified as TEXT")
        return "text"
    else:
        ext = os.path.splitext(name)[1]
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Please upload a PDF, TXT, MD, PNG, JPG, or JPEG file."
        )


def process_uploaded_file(
    filename: str,
    file: Union[str, BinaryIO],
) -> AnalysisRecord:
    """
    Runs the ingestion pipeline for one uploaded file and saves the
    resulting AnalysisRecord to MongoDB's 'analyses' collection.

    Returns the saved AnalysisRecord (with its components populated).
    Raises ValueError if the file type is unsupported.
    """
    analysis_id = str(uuid.uuid4())

    print(f"[service.py] process_uploaded_file called")
    print(f"[service.py]   filename  = {filename!r}")
    print(f"[service.py]   file type = {type(file).__name__}")

    # Classify file before any processing
    try:
        file_class = _classify_file(filename)
    except ValueError:
        # Record the failed attempt then re-raise
        record = AnalysisRecord(
            analysis_id=analysis_id,
            filename=filename,
            raw_text=None,
            components=[],
            status=AnalysisStatus.FAILED.value,
        )
        get_db()["analyses"].insert_one(record.model_dump())
        raise

    try:
        if file_class == "image":
            print(f"[service.py] routing to diagram extractor")
            raw_text = None
            components = extract_components_from_diagram(filename, file)
            print(f"[service.py] diagram extractor returned {len(components)} components")
        else:
            print(f"[service.py] routing to text extractor")
            raw_text = extract_text(filename, file)
            components = detect_components(raw_text)
            print(f"[service.py] text extractor returned {len(components)} components")

        status = AnalysisStatus.ANALYZED.value

    except Exception as e:
        print(f"[service.py] ERROR during extraction: {type(e).__name__}: {e}")
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
    print(f"[service.py] analysis saved with id={analysis_id}")
    return record


def get_analysis_by_id(analysis_id: str) -> AnalysisRecord | None:
    """Fetches a previously saved analysis by its analysis_id."""
    doc = get_db()["analyses"].find_one({"analysis_id": analysis_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return AnalysisRecord(**doc)