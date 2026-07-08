"""
Orchestrates Phase 4:
  analysis_id -> load AnalysisRecord -> map components -> save AtlasMappingRecord
"""

import uuid

from app.db.mongo_client import get_db
from app.db.schemas import AtlasMappingRecord, TechniqueMapping
from app.ingestion.service import get_analysis_by_id
from app.atlas_mapping.mapper import map_components_to_techniques


def run_atlas_mapping(analysis_id: str) -> AtlasMappingRecord:
    """
    Runs the full Phase 4 pipeline for a given analysis and persists
    the result. Raises ValueError if the analysis doesn't exist or has
    no detected components.
    """
    analysis = get_analysis_by_id(analysis_id)
    if analysis is None:
        raise ValueError(f"No analysis found with id '{analysis_id}'.")
    if not analysis.components:
        raise ValueError("This analysis has no detected components to map.")

    raw_results = map_components_to_techniques(analysis.components)
    techniques = [TechniqueMapping(**r) for r in raw_results]

    tactic_summary: dict[str, int] = {}
    for t in techniques:
        tactic_summary[t.tactic_name] = tactic_summary.get(t.tactic_name, 0) + 1

    record = AtlasMappingRecord(
        mapping_id=str(uuid.uuid4()),
        analysis_id=analysis_id,
        techniques=techniques,
        tactic_summary=tactic_summary,
    )

    get_db()["atlas_mappings"].insert_one(record.model_dump())
    return record


def get_latest_mapping(analysis_id: str) -> AtlasMappingRecord | None:
    """Fetches the most recent mapping run for a given analysis."""
    doc = get_db()["atlas_mappings"].find_one(
        {"analysis_id": analysis_id}, sort=[("created_at", -1)]
    )
    if doc is None:
        return None
    doc.pop("_id", None)
    return AtlasMappingRecord(**doc)