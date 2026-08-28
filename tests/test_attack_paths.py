"""Tests for Phase 5 — attack path generation pipeline."""

import pytest
from app.db.schemas import AttackPath, AttackStep, ArchitectureComponent
from app.atlas_mapping.mapper import map_components_to_techniques
from app.attack_paths.risk_scorer import _formula_score, _risk_level
from app.attack_paths.graph_builder import build_attack_graph, get_graph_stats
from app.models.enums import ComponentType

# ── Sample data fixtures ──────────────────────────────────────────────────────

def sample_components():
    return [
        ArchitectureComponent(name="LLM", component_type=ComponentType.LLM.value, confidence=0.9),
        ArchitectureComponent(name="RAG", component_type=ComponentType.RAG.value, confidence=0.85),
        ArchitectureComponent(name="Tool Calling", component_type=ComponentType.TOOL_CALLING.value, confidence=0.8),
    ]


def sample_attack_path():
    return AttackPath(
        path_id="PATH-001",
        name="Test Path",
        entry_point="Crafted email input",
        steps=[
            AttackStep(step=1, technique_id="AML.T0051", technique_name="LLM Prompt Injection",
                      action="Attacker injects prompt", leads_to="Bypasses guardrails"),
            AttackStep(step=2, technique_id="AML.T0053", technique_name="AI Agent Tool Invocation",
                      action="Invokes Gmail tool", leads_to="Accesses email data"),
            AttackStep(step=3, technique_id="AML.T0086", technique_name="Exfiltration via AI Agent Tool",
                      action="Forwards emails to attacker", leads_to="Data exfiltrated"),
        ],
        final_impact="Complete email data exfiltration",
        likelihood=8.0,
        impact=9.0,
        exposure=7.0,
    )


# ── Risk scoring tests ────────────────────────────────────────────────────────

def test_formula_score_high():
    score = _formula_score(8, 9, 7)
    assert score == _formula_score(8, 9, 7)
    assert 61 <= score <= 100


def test_formula_score_low():
    score = _formula_score(2, 2, 2)
    assert score <= 30


def test_risk_level_high():
    assert _risk_level(85.0) == "High"


def test_risk_level_medium():
    assert _risk_level(45.0) == "Medium"


def test_risk_level_low():
    assert _risk_level(20.0) == "Low"


# ── Graph builder tests ───────────────────────────────────────────────────────

def test_build_attack_graph():
    path = sample_attack_path()
    G = build_attack_graph([path])
    assert G.number_of_nodes() == 3
    assert G.number_of_edges() == 2


def test_graph_stats():
    path = sample_attack_path()
    G = build_attack_graph([path])
    stats = get_graph_stats(G)
    assert stats["total_nodes"] == 3
    assert stats["total_edges"] == 2
    assert stats["most_connected_technique"] is not None


def test_multiple_paths_shared_nodes():
    path1 = sample_attack_path()
    path2 = AttackPath(
        path_id="PATH-002",
        name="Second Path",
        entry_point="Different entry",
        steps=[
            AttackStep(step=1, technique_id="AML.T0051", technique_name="LLM Prompt Injection",
                      action="Different action", leads_to="Different outcome"),
            AttackStep(step=2, technique_id="AML.T0070", technique_name="RAG Poisoning",
                      action="Poisons RAG", leads_to="Corrupts responses"),
        ],
        final_impact="Corrupted AI outputs",
        likelihood=6.0, impact=7.0, exposure=5.0,
    )
    G = build_attack_graph([path1, path2])
    # AML.T0051 appears in both paths — should be one node
    assert "AML.T0051" in G.nodes()
    assert G.number_of_nodes() == 4  # T0051, T0053, T0086, T0070


# ── Component → technique mapping test ───────────────────────────────────────

def test_components_produce_techniques():
    components = sample_components()
    mapped = map_components_to_techniques(components)
    assert len(mapped) > 0
    ids = [m.technique_id for m in mapped]
    assert "AML.T0051" in ids   # LLM → Prompt Injection
    assert "AML.T0070" in ids   # RAG → RAG Poisoning
    assert "AML.T0053" in ids   # Tool Calling → Tool Invocation