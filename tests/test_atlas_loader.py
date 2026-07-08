"""Tests for app/atlas_mapping/atlas_loader.py"""

import pytest
from app.atlas_mapping.atlas_loader import get_kb

def test_kb_loads():
    kb = get_kb()
    assert len(kb.tactics) > 0
    assert len(kb.techniques) > 0

def test_known_technique_exists():
    kb = get_kb()
    technique = kb.get_technique("AML.T0051")
    assert technique is not None
    assert technique["name"] == "LLM Prompt Injection"

def test_tactic_lookup_for_technique():
    kb = get_kb()
    tactic_id = kb.tactic_id_for_technique("AML.T0051")
    assert tactic_id is not None
    tactic = kb.get_tactic(tactic_id)
    assert tactic["name"] == "Execution"

def test_subtechnique_falls_back_to_parent_tactic():
    kb = get_kb()
    # AML.T0080.000 is a subtechnique of AML.T0080 (AI Agent Context Poisoning)
    tactic_id = kb.tactic_id_for_technique("AML.T0080.000")
    assert tactic_id is not None