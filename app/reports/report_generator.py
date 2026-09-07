"""
Generates a structured PDF security report using ReportLab.

Report sections:
  1. Cover Page
  2. Executive Summary
  3. Detected Components
  4. MITRE ATLAS Technique Mapping
  5. Attack Paths
  6. Risk Assessment
  7. Mitigation Recommendations
  8. Final Security Score
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable

from app.db.schemas import AnalysisRecord, AttackPathRecord

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0D1B2A")
TEAL   = colors.HexColor("#00B4D8")
WHITE  = colors.white
SLATE  = colors.HexColor("#334155")
LIGHT  = colors.HexColor("#F0F4F8")
RED    = colors.HexColor("#EF4444")
AMBER  = colors.HexColor("#F59E0B")
GREEN  = colors.HexColor("#10B981")
MUTED  = colors.HexColor("#94A3B8")
DARK   = colors.HexColor("#091524")

RISK_COLORS = {
    "High":    RED,
    "Medium":  AMBER,
    "Low":     GREEN,
    "Unknown": MUTED,
}

W, H = A4


# ── Style sheet ───────────────────────────────────────────────────────────────
def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica-Oblique",
            fontSize=13,
            textColor=TEAL,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_label": ParagraphStyle(
            "CoverLabel",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=TEAL,
            spaceAfter=2,
        ),
        "cover_value": ParagraphStyle(
            "CoverValue",
            fontName="Helvetica",
            fontSize=10,
            textColor=WHITE,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=TEAL,
            spaceBefore=16,
            spaceAfter=8,
            borderPad=4,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=WHITE,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10,
            textColor=LIGHT,
            leading=15,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=LIGHT,
            leading=14,
            leftIndent=16,
            spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName="Helvetica",
            fontSize=8,
            textColor=MUTED,
            spaceAfter=2,
        ),
        "risk_high": ParagraphStyle(
            "RiskHigh",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=RED,
        ),
        "risk_medium": ParagraphStyle(
            "RiskMedium",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=AMBER,
        ),
        "risk_low": ParagraphStyle(
            "RiskLow",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=GREEN,
        ),
        "score_big": ParagraphStyle(
            "ScoreBig",
            fontName="Helvetica-Bold",
            fontSize=48,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
    }


# ── Page templates ────────────────────────────────────────────────────────────
def _header_footer(canvas, doc):
    """Draws header and footer on every page except the cover."""
    if doc.page == 1:
        return
    canvas.saveState()

    # Header bar
    canvas.setFillColor(DARK)
    canvas.rect(0, H - 1.2*cm, W, 1.2*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(TEAL)
    canvas.drawString(1.5*cm, H - 0.85*cm, "OpenATLAS Pathfinder")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(W - 1.5*cm, H - 0.85*cm, "AI Security Threat Report")

    # Footer bar
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, W, 1*cm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(1.5*cm, 0.35*cm, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    canvas.drawRightString(W - 1.5*cm, 0.35*cm, f"Page {doc.page}")

    canvas.restoreState()


# ── Table helpers ─────────────────────────────────────────────────────────────
def _header_row_style(col_count: int):
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  TEAL),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("BOTTOMPADDING",(0, 0),(-1, 0),  6),
        ("TOPPADDING",  (0, 0), (-1, 0),  6),
        ("BACKGROUND",  (0, 1), (-1, -1), DARK),
        ("TEXTCOLOR",   (0, 1), (-1, -1), LIGHT),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK, colors.HexColor("#0F2030")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 1),(-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0, 0), (-1, -1), 6),
        ("WORDWRAP",    (0, 0), (-1, -1), True),
    ])


def _risk_badge(level: str) -> str:
    badges = {
        "High":    '<font color="#EF4444"><b>● HIGH</b></font>',
        "Medium":  '<font color="#F59E0B"><b>● MEDIUM</b></font>',
        "Low":     '<font color="#10B981"><b>● LOW</b></font>',
        "Unknown": '<font color="#94A3B8"><b>● UNKNOWN</b></font>',
    }
    return badges.get(level, level)


# ── Main generator ────────────────────────────────────────────────────────────
def generate_pdf_report(
    analysis: AnalysisRecord,
    ap_record: AttackPathRecord,
    overall: dict,
    mitigations: list[dict],
    mapped_techniques: Optional[list[dict]] = None,
) -> bytes:
    """
    Generates the full PDF security report and returns it as bytes.
    The caller writes these bytes to disk or serves them for download.
    """
    buffer = io.BytesIO()
    S = _build_styles()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.8*cm,
        bottomMargin=1.5*cm,
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        W - doc.leftMargin - doc.rightMargin,
        H - doc.topMargin - doc.bottomMargin,
        id="main",
    )
    template = PageTemplate(id="main", frames=[frame], onPage=_header_footer)
    doc.addPageTemplates([template])

    story = []

    # ── COVER PAGE ────────────────────────────────────────────────────────────
    # Full-page navy background
    story.append(Spacer(1, 2.5*cm))
    story.append(Paragraph("🛡️ OpenATLAS Pathfinder", S["title"]))
    story.append(Paragraph("AI Security Threat Report", S["subtitle"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="80%", thickness=1, color=TEAL, spaceAfter=20))
    story.append(Spacer(1, 0.5*cm))

    cover_data = [
        ["File Analysed",   analysis.filename or "N/A"],
        ["Analysis ID",     analysis.analysis_id],
        ["Components Found",str(len(analysis.components))],
        ["Attack Paths",    str(ap_record.total_paths)],
        ["Overall Risk",    overall.get("overall_risk_level", "Unknown")],
        ["Security Score",  f"{overall.get('overall_score', 0):.1f} / 100"],
        ["Generated",       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
    ]

    cover_table = Table(cover_data, colWidths=[5*cm, 10*cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), NAVY),
        ("BACKGROUND",  (1, 0), (1, -1), DARK),
        ("TEXTCOLOR",   (0, 0), (0, -1), TEAL),
        ("TEXTCOLOR",   (1, 0), (1, -1), WHITE),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ("TOPPADDING",  (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="80%", thickness=1, color=TEAL))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "CONFIDENTIAL — For internal security review only. "
        "This report was generated by OpenATLAS Pathfinder for pre-deployment threat modeling purposes.",
        S["small"]
    ))
    story.append(PageBreak())

    # ── SECTION 1 — EXECUTIVE SUMMARY ────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))

    risk_level = overall.get("overall_risk_level", "Unknown")
    score      = overall.get("overall_score", 0)

    summary_text = (
        f"OpenATLAS Pathfinder analysed the AI system architecture described in "
        f"<b>{analysis.filename or 'the uploaded document'}</b>. "
        f"The analysis detected <b>{len(analysis.components)} AI architecture components</b> "
        f"and mapped them to the MITRE ATLAS v2026.06 threat framework. "
        f"The AI reasoning engine generated <b>{ap_record.total_paths} attack paths</b>, "
        f"of which <b>{overall.get('high_count', 0)} are High risk</b>, "
        f"{overall.get('medium_count', 0)} are Medium risk, and "
        f"{overall.get('low_count', 0)} are Low risk. "
        f"The overall security score is <b>{score:.1f}/100</b>, "
        f"classified as <b>{risk_level} Risk</b>. "
        f"Immediate remediation is {'strongly recommended' if risk_level == 'High' else 'recommended'} "
        f"before production deployment."
    )
    story.append(Paragraph(summary_text, S["body"]))
    story.append(Spacer(1, 0.4*cm))

    # Key findings table
    findings = [
        ["Metric", "Value"],
        ["Overall Security Score",  f"{score:.1f} / 100"],
        ["Overall Risk Level",      risk_level],
        ["Components Detected",     str(len(analysis.components))],
        ["ATLAS Techniques Mapped", str(len(mapped_techniques or []))],
        ["Attack Paths Generated",  str(ap_record.total_paths)],
        ["High Risk Paths",         str(overall.get("high_count", 0))],
        ["Avg Likelihood",          f"{overall.get('average_likelihood', 0)}/10"],
        ["Avg Impact",              f"{overall.get('average_impact', 0)}/10"],
        ["Avg Exposure",            f"{overall.get('average_exposure', 0)}/10"],
    ]
    t = Table(findings, colWidths=[8*cm, 7*cm])
    t.setStyle(_header_row_style(2))
    story.append(t)
    story.append(PageBreak())

    # ── SECTION 2 — DETECTED COMPONENTS ──────────────────────────────────────
    story.append(Paragraph("2. Detected Components", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Paragraph(
        "The following AI architecture components were automatically detected from the uploaded input. "
        "Each component type was used to drive ATLAS technique mapping and attack path generation.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    comp_data = [["Component Name", "Type", "Confidence", "Detected From"]]
    for c in analysis.components:
        comp_data.append([
            c.name,
            c.component_type,
            f"{c.confidence:.2f}",
            (c.source_text or "")[:50] + ("..." if c.source_text and len(c.source_text) > 50 else ""),
        ])

    t = Table(comp_data, colWidths=[4*cm, 3.5*cm, 2.5*cm, 5*cm])
    t.setStyle(_header_row_style(4))
    story.append(t)
    story.append(PageBreak())

    # ── SECTION 3 — ATLAS TECHNIQUE MAPPING ──────────────────────────────────
    story.append(Paragraph("3. MITRE ATLAS Technique Mapping", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Paragraph(
        "The detected components were mapped to MITRE ATLAS v2026.06 tactics and techniques. "
        "Each technique represents a known adversarial capability targeting AI systems.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    if mapped_techniques:
        tech_data = [["Technique ID", "Technique Name", "Tactic", "Maturity", "Source"]]
        for t_item in mapped_techniques:
            tech_data.append([
                t_item.get("technique_id", ""),
                t_item.get("technique_name", "")[:35],
                (t_item.get("tactic_name") or "Unknown")[:20],
                t_item.get("maturity", "")[:12],
                t_item.get("source_component", "")[:18],
            ])
        tbl = Table(tech_data, colWidths=[2.5*cm, 5.5*cm, 3*cm, 2*cm, 2*cm])
        tbl.setStyle(_header_row_style(5))
        story.append(tbl)
    else:
        story.append(Paragraph("No technique mapping data available.", S["body"]))

    story.append(PageBreak())

    # ── SECTION 4 — ATTACK PATHS ──────────────────────────────────────────────
    story.append(Paragraph("4. Attack Paths", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Paragraph(
        "The following attack paths were generated by AI reasoning over the detected components "
        "and mapped ATLAS techniques. Each path represents a realistic multi-step attack chain "
        "an adversary could execute against this architecture.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    for path in ap_record.attack_paths:
        risk_color = RISK_COLORS.get(path.risk_level, MUTED)

        # Path header
        path_header = [
            [
                Paragraph(f"{path.path_id} — {path.name}", S["h2"]),
                Paragraph(_risk_badge(path.risk_level), S["body"]),
            ]
        ]
        ph_table = Table(path_header, colWidths=[12*cm, 3*cm])
        ph_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), DARK),
            ("TOPPADDING",  (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0),(-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW",   (0, 0), (-1, -1), 1.5, risk_color),
        ]))
        story.append(KeepTogether([ph_table]))
        story.append(Spacer(1, 0.15*cm))

        # Scores row
        scores_data = [[
            f"Risk Score: {path.risk_score:.1f}/100",
            f"Likelihood: {path.likelihood}/10",
            f"Impact: {path.impact}/10",
            f"Exposure: {path.exposure}/10",
        ]]
        scores_tbl = Table(scores_data, colWidths=[3.75*cm]*4)
        scores_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, -1), TEAL),
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0),(-1, -1), 5),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#1E3A5F")),
        ]))
        story.append(scores_tbl)
        story.append(Spacer(1, 0.15*cm))

        story.append(Paragraph(f"<b>Entry Point:</b> {path.entry_point}", S["body"]))
        story.append(Paragraph(f"<b>Final Impact:</b> {path.final_impact}", S["body"]))

        if path.ai_explanation:
            story.append(Paragraph(
                f"<b>AI Risk Analysis:</b> {path.ai_explanation}", S["body"]
            ))

        # Steps table
        steps_data = [["Step", "Technique ID", "Technique Name", "Attacker Action"]]
        for step in path.steps:
            steps_data.append([
                str(step.step),
                step.technique_id,
                step.technique_name[:30],
                step.action[:55],
            ])

        steps_tbl = Table(steps_data, colWidths=[1*cm, 2.5*cm, 4.5*cm, 7*cm])
        steps_tbl.setStyle(_header_row_style(4))
        story.append(steps_tbl)
        story.append(Spacer(1, 0.5*cm))

    story.append(PageBreak())

    # ── SECTION 5 — RISK ASSESSMENT ───────────────────────────────────────────
    story.append(Paragraph("5. Risk Assessment", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Paragraph(
        "Risk scores are calculated using the formula: "
        "<b>Risk Score = (Likelihood × Impact × Exposure) / 10</b>. "
        "Scores are classified as Low (0–30), Medium (31–60), or High (61–100). "
        "Likelihood, Impact, and Exposure scores are generated by the Gemini AI model "
        "with context specific to the detected architecture.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    risk_data = [["Path", "Likelihood", "Impact", "Exposure", "Score", "Level"]]
    for path in sorted(ap_record.attack_paths, key=lambda p: p.risk_score, reverse=True):
        risk_data.append([
            path.name[:28],
            f"{path.likelihood}/10",
            f"{path.impact}/10",
            f"{path.exposure}/10",
            f"{path.risk_score:.1f}",
            path.risk_level,
        ])

    risk_tbl = Table(risk_data, colWidths=[5.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm])
    style = _header_row_style(6)

    # Colour risk level cells
    for i, path in enumerate(
        sorted(ap_record.attack_paths, key=lambda p: p.risk_score, reverse=True), 1
    ):
        c = RISK_COLORS.get(path.risk_level, MUTED)
        style.add("TEXTCOLOR", (5, i), (5, i), c)
        style.add("FONTNAME",  (5, i), (5, i), "Helvetica-Bold")

    risk_tbl.setStyle(style)
    story.append(risk_tbl)
    story.append(PageBreak())

    # ── SECTION 6 — MITIGATIONS ───────────────────────────────────────────────
    story.append(Paragraph("6. Mitigation Recommendations", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Paragraph(
        "The following mitigations are recommended, prioritised by the number of attack paths "
        "each control addresses. Mitigations are generated by AI reasoning specific to this "
        "architecture and mapped to MITRE ATLAS mitigation IDs where applicable.",
        S["body"]
    ))
    story.append(Spacer(1, 0.3*cm))

    mit_data = [["Mitigation", "Type", "Effort", "Paths", "ATLAS ID"]]
    for m in mitigations:
        mit_data.append([
            m.get("title", "")[:35],
            m.get("control_type", ""),
            m.get("effort", ""),
            str(m.get("addresses_paths", 0)),
            m.get("atlas_mitigation_id", "—"),
        ])

    mit_tbl = Table(mit_data, colWidths=[6*cm, 2.5*cm, 2*cm, 1.5*cm, 3*cm])
    mit_tbl.setStyle(_header_row_style(5))
    story.append(mit_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Detailed descriptions
    story.append(Paragraph("Mitigation Details:", S["h2"]))
    for m in mitigations[:8]:
        icons = {"Preventive": "🛡", "Detective": "🔍", "Corrective": "🔧"}
        icon  = icons.get(m.get("control_type", ""), "•")
        story.append(Paragraph(
            f"<b>{icon} {m.get('title', '')}</b> "
            f"({m.get('control_type', '')} | Effort: {m.get('effort', '')})",
            S["bullet"]
        ))
        story.append(Paragraph(m.get("description", ""), S["bullet"]))
        story.append(Spacer(1, 0.15*cm))

    story.append(PageBreak())

    # ── SECTION 7 — FINAL SCORE ───────────────────────────────────────────────
    story.append(Paragraph("7. Final Security Score", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=TEAL, spaceAfter=8))
    story.append(Spacer(1, 0.5*cm))

    risk_level  = overall.get("overall_risk_level", "Unknown")
    final_color = RISK_COLORS.get(risk_level, MUTED)

    score_style = ParagraphStyle(
        "ScoreFinal",
        fontName="Helvetica-Bold",
        fontSize=60,
        textColor=final_color,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    story.append(Paragraph(f"{overall.get('overall_score', 0):.1f}", score_style))
    story.append(Paragraph("out of 100", S["subtitle"]))
    story.append(Spacer(1, 0.3*cm))

    level_style = ParagraphStyle(
        "LevelFinal",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=final_color,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    story.append(Paragraph(f"{risk_level.upper()} RISK", level_style))
    story.append(HRFlowable(width="60%", thickness=2, color=final_color, spaceAfter=16))
    story.append(Spacer(1, 0.3*cm))

    rec_map = {
        "High": (
            "IMMEDIATE ACTION REQUIRED. This architecture presents significant AI security risks "
            "that must be addressed before production deployment. Priority mitigations should be "
            "implemented immediately, focusing on the High risk attack paths identified in Section 4."
        ),
        "Medium": (
            "ACTION RECOMMENDED. This architecture presents moderate AI security risks. "
            "A structured remediation plan should be developed and executed before deployment. "
            "Focus on the mitigations listed in Section 6."
        ),
        "Low": (
            "LOW RISK. This architecture presents manageable AI security risks. "
            "Standard security hygiene and the listed mitigations are sufficient for deployment. "
            "Schedule periodic re-assessments as the architecture evolves."
        ),
    }
    story.append(Paragraph(rec_map.get(risk_level, "Complete a full security review."), S["body"]))
    story.append(Spacer(1, 0.5*cm))

    # Score breakdown summary table
    final_data = [
        ["Metric",              "Value"],
        ["Overall Score",       f"{overall.get('overall_score', 0):.1f}/100"],
        ["Risk Level",          risk_level],
        ["Highest Path Score",  f"{overall.get('highest_score', 0):.1f}/100"],
        ["Highest Risk Path",   overall.get("highest_path_name", "N/A")],
        ["Avg Likelihood",      f"{overall.get('average_likelihood', 0)}/10"],
        ["Avg Impact",          f"{overall.get('average_impact', 0)}/10"],
        ["Avg Exposure",        f"{overall.get('average_exposure', 0)}/10"],
        ["Total Paths",         str(overall.get("total_paths", 0))],
        ["High Risk Paths",     str(overall.get("high_count", 0))],
        ["Medium Risk Paths",   str(overall.get("medium_count", 0))],
        ["Low Risk Paths",      str(overall.get("low_count", 0))],
    ]
    ft = Table(final_data, colWidths=[8*cm, 7*cm])
    ft.setStyle(_header_row_style(2))
    story.append(ft)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "This report was generated by OpenATLAS Pathfinder — an open-source AI Threat Modeling platform. "
        "Techniques are mapped to MITRE ATLAS v2026.06. Attack paths and risk scores are generated "
        "by Google Gemini AI and validated against the local ATLAS knowledge base.",
        S["small"]
    ))

    doc.build(story)
    return buffer.getvalue()