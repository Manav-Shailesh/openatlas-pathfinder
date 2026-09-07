"""Tests for Phase 8 — PDF report generation."""

import pytest
from app.db.schemas import (
    AnalysisRecord, AttackPathRecord, AttackPath,
    AttackStep, ArchitectureComponent,
)
from app.risk_scoring.scoring_summary import compute_overall_score, compute_mitigation_summary
from app.reports.report_generator import generate_pdf_report


def sample_analysis():
    return AnalysisRecord(
        analysis_id="test-report-001",
        filename="sample_architecture.txt",
        raw_text="GPT-4 LLM with RAG and Gmail tool calling.",
        components=[
            ArchitectureComponent(
                name="LLM (GPT-4)",
                component_type="LLM",
                confidence=0.95,
                source_text="gpt-4",
            ),
            ArchitectureComponent(
                name="RAG Pipeline",
                component_type="RAG",
                confidence=0.88,
                source_text="rag pipeline",
            ),
        ],
        status="analyzed",
    )


def sample_ap_record():
    return AttackPathRecord(
        analysis_id="test-report-001",
        filename="sample_architecture.txt",
        attack_paths=[
            AttackPath(
                path_id="PATH-001",
                name="Indirect Prompt Injection via Gmail",
                entry_point="Attacker sends crafted email",
                steps=[
                    AttackStep(
                        step=1,
                        technique_id="AML.T0051",
                        technique_name="LLM Prompt Injection",
                        action="Inject malicious prompt via email",
                        leads_to="Bypasses agent guardrails",
                    ),
                    AttackStep(
                        step=2,
                        technique_id="AML.T0086",
                        technique_name="Exfiltration via AI Agent Tool",
                        action="Forward emails to attacker",
                        leads_to="Data exfiltrated",
                    ),
                ],
                final_impact="Complete email data exfiltration",
                likelihood=8.0,
                impact=9.0,
                exposure=7.0,
                risk_score=50.4,
                risk_level="Medium",
                ai_explanation="The Gmail integration creates a zero-click attack surface.",
                mitigations=[
                    {
                        "title": "Implement Guardrails",
                        "description": "Add input/output guardrails to the LLM pipeline.",
                        "control_type": "Preventive",
                        "effort": "Medium",
                        "atlas_mitigation_id": "AML.M0020",
                    }
                ],
            )
        ],
        total_paths=1,
        highest_risk_score=50.4,
        overall_risk_level="Medium",
        status="complete",
    )


def test_generate_pdf_returns_bytes():
    analysis  = sample_analysis()
    ap_record = sample_ap_record()
    overall   = compute_overall_score(ap_record)
    mitigations = compute_mitigation_summary(ap_record)

    pdf_bytes = generate_pdf_report(
        analysis=analysis,
        ap_record=ap_record,
        overall=overall,
        mitigations=mitigations,
        mapped_techniques=[],
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000


def test_pdf_starts_with_pdf_header():
    analysis    = sample_analysis()
    ap_record   = sample_ap_record()
    overall     = compute_overall_score(ap_record)
    mitigations = compute_mitigation_summary(ap_record)

    pdf_bytes = generate_pdf_report(
        analysis=analysis,
        ap_record=ap_record,
        overall=overall,
        mitigations=mitigations,
    )
    # All valid PDFs start with %PDF
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_with_empty_mitigations():
    analysis    = sample_analysis()
    ap_record   = sample_ap_record()
    overall     = compute_overall_score(ap_record)

    pdf_bytes = generate_pdf_report(
        analysis=analysis,
        ap_record=ap_record,
        overall=overall,
        mitigations=[],
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000


def test_pdf_with_mapped_techniques():
    analysis    = sample_analysis()
    ap_record   = sample_ap_record()
    overall     = compute_overall_score(ap_record)
    mitigations = compute_mitigation_summary(ap_record)

    techniques = [
        {
            "technique_id":   "AML.T0051",
            "technique_name": "LLM Prompt Injection",
            "tactic_name":    "Execution",
            "maturity":       "Realized",
            "source_component": "LLM",
        }
    ]

    pdf_bytes = generate_pdf_report(
        analysis=analysis,
        ap_record=ap_record,
        overall=overall,
        mitigations=mitigations,
        mapped_techniques=techniques,
    )
    assert pdf_bytes[:4] == b"%PDF"