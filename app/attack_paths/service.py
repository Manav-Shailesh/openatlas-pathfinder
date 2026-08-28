"""
Orchestrates the full Phase 5 pipeline:
  AnalysisRecord (components + mapped techniques)
    → Gemini generates attack paths
    → Gemini scores each path
    → Gemini generates mitigations
    → Save AttackPathRecord to MongoDB
    → Return results
"""

from app.db.mongo_client import get_db
from app.db.schemas import AttackPath, AttackPathRecord, AnalysisRecord
from app.atlas_mapping.mapper import map_components_to_techniques
from app.attack_paths.ai_path_generator import generate_attack_paths
from app.attack_paths.risk_scorer import score_all_paths
from app.attack_paths.mitigation_engine import generate_all_mitigations
from app.attack_paths.graph_builder import build_attack_graph, get_graph_stats


def run_attack_path_pipeline(
    record: AnalysisRecord,
) -> AttackPathRecord:
    """
    Full Phase 5 pipeline for one analysis record.
    Steps:
      1. Map components to ATLAS techniques
      2. Gemini generates attack paths
      3. Gemini scores each path (L × I × E + AI explanation)
      4. Gemini generates specific mitigations
      5. Save to MongoDB
      6. Return AttackPathRecord
    """
    analysis_id = record.analysis_id
    components_raw = [c.model_dump() for c in record.components]

    print(f"[service] Starting attack path pipeline for {analysis_id}")

    # Step 1 — ATLAS mapping
    mapped_techniques = map_components_to_techniques(record.components)
    if not mapped_techniques:
        return _save_empty_record(analysis_id, record.filename, "No techniques mapped")

    # Step 2 — AI attack path generation
    attack_paths = generate_attack_paths(components_raw, mapped_techniques)
    if not attack_paths:
        return _save_empty_record(analysis_id, record.filename, "No paths generated")

    # Step 3 — AI risk scoring
    attack_paths = score_all_paths(attack_paths, components_raw)

    # Step 4 — AI mitigations
    attack_paths = generate_all_mitigations(attack_paths, components_raw)

    # Step 5 — Calculate summary stats
    highest_score = max(p.risk_score for p in attack_paths) if attack_paths else 0.0
    if highest_score >= 61:
        overall_level = "High"
    elif highest_score >= 31:
        overall_level = "Medium"
    else:
        overall_level = "Low"

    result = AttackPathRecord(
        analysis_id=analysis_id,
        filename=record.filename,
        attack_paths=attack_paths,
        total_paths=len(attack_paths),
        highest_risk_score=highest_score,
        overall_risk_level=overall_level,
        status="complete",
    )

    # Step 6 — Save to MongoDB
    db = get_db()
    db["attack_path_records"].replace_one(
        {"analysis_id": analysis_id},
        result.model_dump(),
        upsert=True,
    )
    print(f"[service] Saved {len(attack_paths)} paths for {analysis_id}")
    return result


def get_attack_path_record(analysis_id: str) -> AttackPathRecord | None:
    """Fetches a saved AttackPathRecord from MongoDB."""
    doc = get_db()["attack_path_records"].find_one({"analysis_id": analysis_id})
    if doc is None:
        return None
    doc.pop("_id", None)
    return AttackPathRecord(**doc)


def _save_empty_record(
    analysis_id: str,
    filename: str | None,
    reason: str,
) -> AttackPathRecord:
    record = AttackPathRecord(
        analysis_id=analysis_id,
        filename=filename,
        attack_paths=[],
        total_paths=0,
        overall_risk_level="Unknown",
        status=f"failed: {reason}",
    )
    get_db()["attack_path_records"].replace_one(
        {"analysis_id": analysis_id},
        record.model_dump(),
        upsert=True,
    )
    return record