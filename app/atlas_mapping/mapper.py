"""
Core mapping logic: takes a list of ArchitectureComponent (from Phase 2/2.5)
and returns a deduplicated list of matched ATLAS techniques, each annotated
with which component(s) triggered it.

Deliberately works off flat component_type only (no graph/relationship
data) since Phase 3 isn't wired in yet. Upgrading this later to use
component relationships is additive, not a rewrite.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from app.atlas_mapping.atlas_loader import get_kb
from app.db.schemas import ArchitectureComponent

MAPPING_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "atlas_knowledge_base" / "component_technique_mapping.json"
)


@lru_cache(maxsize=1)
def _load_component_mapping() -> dict:
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(f"component_technique_mapping.json not found at {MAPPING_PATH}")
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def map_components_to_techniques(components: List[ArchitectureComponent]) -> list[dict]:
    """
    Returns a list of dicts (matching the TechniqueMapping schema fields)
    sorted by tactic name, then technique id. Each technique appears once
    even if multiple components triggered it - matched_components lists
    all of them.
    """
    kb = get_kb()
    component_mapping = _load_component_mapping()

    results: dict[str, dict] = {}

    for component in components:
        technique_ids = component_mapping.get(component.component_type, [])
        for tid in technique_ids:
            technique = kb.get_technique(tid)
            if technique is None:
                continue  # ID in our mapping doesn't exist in this ATLAS release — skip safely

            tactic_id = kb.tactic_id_for_technique(tid)
            tactic = kb.get_tactic(tactic_id) if tactic_id else None

            if tid not in results:
                results[tid] = {
                    "technique_id": tid,
                    "technique_name": technique["name"],
                    "tactic_id": tactic_id,
                    "tactic_name": tactic["name"] if tactic else "Unknown",
                    "maturity": technique.get("maturity"),
                    "url": f"https://atlas.mitre.org/techniques/{tid}",
                    "matched_components": [],
                }
            if component.name not in results[tid]["matched_components"]:
                results[tid]["matched_components"].append(component.name)

    return sorted(results.values(), key=lambda r: (r["tactic_name"] or "", r["technique_id"]))