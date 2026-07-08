"""
Tests for app/ingestion/diagram_extractor.py

Live tests (marked with @requires_api_key) call the real Gemini API
and are skipped automatically if GOOGLE_API_KEY is not set.
"""

import pytest
from app.config import settings
from app.ingestion.diagram_extractor import extract_components_from_diagram

requires_api_key = pytest.mark.skipif(
    not settings.GOOGLE_API_KEY,
    reason="GOOGLE_API_KEY not set — skipping live Gemini tests",
)


def test_unsupported_format_raises():
    """BMP files should raise ValueError before any API call."""
    with pytest.raises(ValueError, match="Unsupported image type"):
        extract_components_from_diagram(
            "diagram.bmp",
            "data/sample_docs/sample_architecture.txt",
        )


def test_missing_api_key_raises(monkeypatch):
    """Should raise ValueError with helpful message when key is absent."""
    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "")
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        extract_components_from_diagram(
            "diagram.png",
            "data/sample_docs/sample_architecture.txt",
        )


@requires_api_key
def test_extract_from_sample_diagram():
    """
    Live test: send sample_diagram.png to Gemini and confirm we get
    back a list of ArchitectureComponent objects.
    Add your own sample diagram to data/sample_docs/ to run this.
    """
    with open("data/sample_docs/sample_diagram.png", "rb") as f:
        components = extract_components_from_diagram("sample_diagram.png", f)

    assert isinstance(components, list)
    for c in components:
        assert 0.0 <= c.confidence <= 1.0
        assert c.component_type in {ct.value for ct in __import__(
            'app.models.enums', fromlist=['ComponentType']
        ).ComponentType}