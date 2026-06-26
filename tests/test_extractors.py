"""Tests for app/ingestion/extractors.py"""

import io
from app.ingestion.extractors import extract_text, extract_from_txt


def test_extract_txt_from_path():
    text = extract_text(
        "sample_architecture.txt",
        "data/sample_docs/sample_architecture.txt",
    )
    assert "GPT-4" in text
    assert "Pinecone" in text


def test_extract_txt_from_file_like():
    fake_file = io.BytesIO(b"Hello Gmail Integration")
    text = extract_from_txt(fake_file)
    assert "Gmail" in text


def test_unsupported_extension_raises():
    import pytest
    with pytest.raises(ValueError):
        extract_text("diagram.png", "data/sample_docs/sample_architecture.txt")