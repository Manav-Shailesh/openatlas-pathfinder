"""
Loads and caches the official MITRE ATLAS dataset (ATLAS.yaml) and
provides lookup helpers: technique -> tactic, technique -> full details.

The YAML schema (verified against the real v2026.06 release):
  tactics: { "AML.TAxxxx": {name, description, ...}, ... }
  techniques: { "AML.Txxxx": {name, description, maturity, ...}, ... }
  relationships: { "AML.Txxxx": {"achieves": [{"target": "AML.TAxxxx"}]}, ... }
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

ATLAS_YAML_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "atlas_knowledge_base" / "ATLAS.yaml"
)


class AtlasKnowledgeBase:
    def __init__(self, path: Path = ATLAS_YAML_PATH):
        if not path.exists():
            raise FileNotFoundError(
                f"ATLAS.yaml not found at {path}. Download it first — see "
                "Phase 4 setup instructions (curl command in README)."
            )
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.version: str = data.get("collection", {}).get("version", "unknown")
        self.tactics: dict = data.get("tactics", {})
        self.techniques: dict = data.get("techniques", {})
        self.relationships: dict = data.get("relationships", {})

    def get_technique(self, technique_id: str) -> Optional[dict]:
        return self.techniques.get(technique_id)

    def get_tactic(self, tactic_id: str) -> Optional[dict]:
        return self.tactics.get(tactic_id)

    def tactic_id_for_technique(self, technique_id: str) -> Optional[str]:
        """
        Looks up which tactic a technique 'achieves'. Subtechniques
        (e.g. AML.T0080.000) sometimes don't have their own relationship
        entry, so we fall back to the parent technique's tactic.
        """
        rel = self.relationships.get(technique_id, {})
        for edge in rel.get("achieves", []):
            return edge["target"]

        if technique_id.count(".") >= 2:
            parent_id = technique_id.rsplit(".", 1)[0]
            return self.tactic_id_for_technique(parent_id)

        return None

@lru_cache(maxsize=1)
def get_kb() -> AtlasKnowledgeBase:
    """Cached singleton, same pattern as get_db() in mongo_client.py."""
    return AtlasKnowledgeBase()