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
"""
Maps detected ArchitectureComponents to MITRE ATLAS techniques.

Flow:
  List[ArchitectureComponent]
    -> look up each component_type in component_technique_map.json
    -> for each technique ID, fetch full details from ATLAS knowledge base
    -> return List[MappedTechnique] with tactic, technique, confidence, source component
"""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.atlas_mapping.atlas_loader import get_kb
from app.db.schemas import ArchitectureComponent

COMPONENT_MAP_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "atlas_knowledge_base" / "component_technique_mapping.json"
)


class MappedTechnique(BaseModel):
    """A single ATLAS technique matched to a detected architecture component."""
    technique_id: str
    technique_name: str
    tactic_id: Optional[str] = None
    tactic_name: Optional[str] = None
    description: str = ""
    maturity: str = ""
    source_component: str       # which ComponentType triggered this match
    confidence: float           # inherited from the ArchitectureComponent confidence


def _load_component_map() -> dict[str, list[str]]:
    if not COMPONENT_MAP_PATH.exists():
        raise FileNotFoundError(
            f"component_technique_map.json not found at {COMPONENT_MAP_PATH}"
        )
    with open(COMPONENT_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def map_components_to_techniques(
    components: list[ArchitectureComponent],
) -> list[MappedTechnique]:
    """
    For every detected component, look up its known ATLAS technique IDs
    and resolve each one to full ATLAS data.

    Deduplicates: if the same technique appears via multiple components
    (e.g. both RAG and Vector DB map to AML.T0085.000) only the first
    occurrence is kept, preserving the highest-confidence source.
    """
    kb = get_kb()
    component_map = _load_component_map()

    seen_technique_ids: set[str] = set()
    results: list[MappedTechnique] = []

    for component in components:
        component_type = component.component_type
        technique_ids = component_map.get(component_type, [])

        for technique_id in technique_ids:
            if technique_id in seen_technique_ids:
                continue
            seen_technique_ids.add(technique_id)

            technique = kb.get_technique(technique_id)
            if technique is None:
                continue

            tactic_id = kb.tactic_id_for_technique(technique_id)
            tactic = kb.get_tactic(tactic_id) if tactic_id else None

            results.append(
                MappedTechnique(
                    technique_id=technique_id,
                    technique_name=technique.get("name", "Unknown"),
                    tactic_id=tactic_id,
                    tactic_name=tactic.get("name") if tactic else None,
                    description=technique.get("description", "")[:300],
                    maturity=technique.get("maturity", ""),
                    source_component=component_type,
                    confidence=component.confidence,
                )
            )

    results.sort(key=lambda t: t.confidence, reverse=True)
    return results


def summarise_by_tactic(
    mapped: list[MappedTechnique],
) -> dict[str, list[MappedTechnique]]:
    """Groups MappedTechniques by tactic name for dashboard display."""
    grouped: dict[str, list[MappedTechnique]] = {}
    for m in mapped:
        key = m.tactic_name or "Unknown Tactic"
        grouped.setdefault(key, []).append(m)
    return grouped