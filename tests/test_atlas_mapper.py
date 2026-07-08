"""
Tests for Phase 4 — ATLAS knowledge base loading and component mapping.
"""

import pytest
from app.atlas_mapping.atlas_loader import get_kb, AtlasKnowledgeBase
from app.atlas_mapping.mapper import map_components_to_techniques, MappedTechnique
from app.db.schemas import ArchitectureComponent
from app.models.enums import ComponentType


def test_kb_loads():
    kb = get_kb()
    assert kb.version != "unknown"
    assert len(kb.tactics) > 0
    assert len(kb.techniques) > 0


def test_known_technique_exists():
    kb = get_kb()
    technique = kb.get_technique("AML.T0051")
    assert technique is not None
    assert "Prompt Injection" in technique["name"]


def test_known_tactic_exists():
    kb = get_kb()
    tactic = kb.get_tactic("AML.TA0005")
    assert tactic is not None
    assert "Execution" in tactic["name"]


def test_tactic_id_for_technique():
    kb = get_kb()
    tactic_id = kb.tactic_id_for_technique("AML.T0051")
    assert tactic_id == "AML.TA0005"


def test_subtechnique_fallback():
    """Subtechnique with no direct relationship should fall back to parent."""
    kb = get_kb()
    tactic_id = kb.tactic_id_for_technique("AML.T0080.000")
    assert tactic_id is not None


def test_map_llm_component():
    components = [
        ArchitectureComponent(
            name="LLM",
            component_type=ComponentType.LLM.value,
            confidence=0.9,
        )
    ]
    mapped = map_components_to_techniques(components)
    assert len(mapped) > 0
    technique_ids = [m.technique_id for m in mapped]
    assert "AML.T0051" in technique_ids


def test_map_rag_component():
    components = [
        ArchitectureComponent(
            name="RAG Pipeline",
            component_type=ComponentType.RAG.value,
            confidence=0.85,
        )
    ]
    mapped = map_components_to_techniques(components)
    technique_ids = [m.technique_id for m in mapped]
    assert "AML.T0070" in technique_ids


def test_no_duplicate_techniques():
    """Same technique from two components should appear only once."""
    components = [
        ArchitectureComponent(
            name="RAG",
            component_type=ComponentType.RAG.value,
            confidence=0.9,
        ),
        ArchitectureComponent(
            name="Knowledge Base",
            component_type=ComponentType.KNOWLEDGE_BASE.value,
            confidence=0.7,
        ),
    ]
    mapped = map_components_to_techniques(components)
    ids = [m.technique_id for m in mapped]
    assert len(ids) == len(set(ids)), "Duplicate technique IDs found"


def test_mapped_technique_has_tactic():
    components = [
        ArchitectureComponent(
            name="Agent",
            component_type=ComponentType.AGENT.value,
            confidence=0.8,
        )
    ]
    mapped = map_components_to_techniques(components)
    for m in mapped:
        assert m.tactic_id is not None
        assert m.tactic_name is not None


def test_results_sorted_by_confidence():
    components = [
        ArchitectureComponent(
            name="LLM",
            component_type=ComponentType.LLM.value,
            confidence=0.5,
        ),
        ArchitectureComponent(
            name="Agent",
            component_type=ComponentType.AGENT.value,
            confidence=0.9,
        ),
    ]
    mapped = map_components_to_techniques(components)
    confidences = [m.confidence for m in mapped]
    assert confidences == sorted(confidences, reverse=True)