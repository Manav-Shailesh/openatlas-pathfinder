"""Tests for Phase 6 — risk scoring and dashboard data."""

import pytest
from app.db.schemas import AttackPathRecord, AttackPath, AttackStep
from app.risk_scoring.scoring_summary import (
    compute_overall_score,
    compute_tactic_breakdown,
    compute_mitigation_summary,
)
from app.risk_scoring.heatmap import (
    build_risk_gauge,
    build_path_score_chart,
    build_lia_chart,
    build_risk_heatmap,
)


def make_path(path_id, name, risk_score, risk_level,
              likelihood, impact, exposure, mitigations=None):
    return AttackPath(
        path_id=path_id,
        name=name,
        entry_point="Test entry",
        steps=[
            AttackStep(
                step=1,
                technique_id="AML.T0051",
                technique_name="LLM Prompt Injection",
                action="Test action",
                leads_to="Test outcome",
            )
        ],
        final_impact="Test impact",
        likelihood=likelihood,
        impact=impact,
        exposure=exposure,
        risk_score=risk_score,
        risk_level=risk_level,
        ai_explanation="Test explanation",
        mitigations=mitigations or [],
    )


def sample_record():
    return AttackPathRecord(
        analysis_id="test-123",
        filename="test.txt",
        attack_paths=[
            make_path("P1", "High Risk Path",   84.0, "High",   9, 9, 8,
                      [{"title": "Use Guardrails", "description": "Add guardrails",
                        "control_type": "Preventive", "effort": "Medium",
                        "atlas_mitigation_id": "AML.M0020"}]),
            make_path("P2", "Medium Risk Path", 45.0, "Medium", 6, 7, 6,
                      [{"title": "Use Guardrails", "description": "Add guardrails",
                        "control_type": "Preventive", "effort": "Medium",
                        "atlas_mitigation_id": "AML.M0020"},
                       {"title": "Enable Logging", "description": "Add telemetry",
                        "control_type": "Detective", "effort": "Low",
                        "atlas_mitigation_id": "AML.M0024"}]),
            make_path("P3", "Low Risk Path",    20.0, "Low",    3, 3, 3),
        ],
        total_paths=3,
        highest_risk_score=84.0,
        overall_risk_level="High",
        status="complete",
    )


# ── Scoring summary tests ─────────────────────────────────────────────────────

def test_compute_overall_score_returns_dict():
    result = compute_overall_score(sample_record())
    assert isinstance(result, dict)
    assert "overall_score" in result
    assert "overall_risk_level" in result


def test_overall_score_range():
    result = compute_overall_score(sample_record())
    assert 0 <= result["overall_score"] <= 100


def test_overall_risk_level_is_high():
    result = compute_overall_score(sample_record())
    assert result["overall_risk_level"] == "High"


def test_counts_correct():
    result = compute_overall_score(sample_record())
    assert result["high_count"]   == 1
    assert result["medium_count"] == 1
    assert result["low_count"]    == 1
    assert result["total_paths"]  == 3


def test_empty_record_returns_zeros():
    empty = AttackPathRecord(
        analysis_id="empty",
        attack_paths=[],
        total_paths=0,
        overall_risk_level="Unknown",
    )
    result = compute_overall_score(empty)
    assert result["overall_score"] == 0.0
    assert result["total_paths"]   == 0


def test_mitigation_summary_deduplication():
    result = compute_mitigation_summary(sample_record())
    titles = [m["title"] for m in result]
    # "Use Guardrails" appears in 2 paths — should appear once
    assert titles.count("Use Guardrails") == 1


def test_mitigation_summary_sorted_by_path_count():
    result = compute_mitigation_summary(sample_record())
    # "Use Guardrails" addresses 2 paths — should be first
    assert result[0]["title"] == "Use Guardrails"
    assert result[0]["addresses_paths"] == 2


# ── Chart builder tests ───────────────────────────────────────────────────────

def test_build_risk_gauge_returns_figure():
    import plotly.graph_objects as go
    fig = build_risk_gauge(75.0, "High")
    assert isinstance(fig, go.Figure)


def test_build_path_score_chart_returns_figure():
    import plotly.graph_objects as go
    fig = build_path_score_chart(sample_record())
    assert isinstance(fig, go.Figure)


def test_build_lia_chart_returns_figure():
    import plotly.graph_objects as go
    fig = build_lia_chart(sample_record())
    assert isinstance(fig, go.Figure)


def test_build_risk_heatmap_returns_figure():
    import plotly.graph_objects as go
    components = [
        {"component_type": "LLM"},
        {"component_type": "RAG"},
    ]
    fig = build_risk_heatmap(sample_record(), components)
    assert isinstance(fig, go.Figure)