"""Tests for app/ingestion/component_detector.py"""

from app.ingestion.component_detector import detect_components
from app.models.enums import ComponentType

SAMPLE_TEXT = """
Our system uses GPT-4 as the core LLM, with a RAG pipeline backed by
Pinecone as the vector database. We use Agent Memory to persist
conversation history. Tool Calling is enabled for Gmail Integration
and Slack Integration.
"""


def test_detects_expected_components():
    components = detect_components(SAMPLE_TEXT)
    detected_types = {c.component_type for c in components}

    assert ComponentType.LLM.value in detected_types
    assert ComponentType.RAG.value in detected_types
    assert ComponentType.VECTOR_DB.value in detected_types
    assert ComponentType.TOOL_CALLING.value in detected_types
    assert ComponentType.EXTERNAL_API.value in detected_types
    assert ComponentType.MEMORY.value in detected_types


def test_confidence_is_within_bounds():
    components = detect_components(SAMPLE_TEXT)
    for c in components:
        assert 0.0 <= c.confidence <= 1.0


def test_no_components_in_unrelated_text():
    components = detect_components("This is a sentence about gardening and cooking.")
    assert components == []