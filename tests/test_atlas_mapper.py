"""Tests for app/atlas_mapping/mapper.py"""

from app.atlas_mapping.mapper import map_components_to_techniques
from app.db.schemas import ArchitectureComponent
from app.models.enums import ComponentType

def _component(component_type: ComponentType, name: str = None) -> ArchitectureComponent:
    return ArchitectureComponent(
        name=name or component_type.value,
        component_type=component_type.value,
        confidence=0.9,
    )

def test_llm_component_maps_to_prompt_injection():
    results = map_components_to_techniques([_component(ComponentType.LLM)])
    technique_ids = {r["technique_id"] for r in results}
    assert "AML.T0051" in technique_ids

def test_tool_calling_maps_to_agent_tool_techniques():
    results = map_components_to_techniques([_component(ComponentType.TOOL_CALLING)])
    technique_ids = {r["technique_id"] for r in results}
    assert "AML.T0053" in technique_ids
    assert "AML.T0086" in technique_ids

def test_shared_technique_lists_both_components():
    # RAG and Knowledge Base both map to AML.T0085.000 (RAG Databases)
    results = map_components_to_techniques([
        _component(ComponentType.KNOWLEDGE_BASE, "Internal KB"),
        _component(ComponentType.VECTOR_DB, "Pinecone"),
    ])
    match = next(r for r in results if r["technique_id"] == "AML.T0085.000")
    assert "Internal KB" in match["matched_components"]
    assert "Pinecone" in match["matched_components"]

def test_empty_component_list_returns_empty():
    assert map_components_to_techniques([]) == []