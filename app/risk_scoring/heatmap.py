"""
Generates Plotly visualisations for the risk dashboard:
  1. Component × Tactic risk heatmap
  2. Risk score bar chart per attack path
  3. Likelihood / Impact / Exposure radar chart
"""

from typing import Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from app.db.schemas import AttackPathRecord, AttackPath

# Risk level → numeric value for heatmap colouring
_RISK_NUMERIC = {"High": 3, "Medium": 2, "Low": 1, "Unknown": 0}
_RISK_COLORS  = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"}
_BG           = "#0D1B2A"
_PAPER        = "#091524"
_TEXT         = "#E2E8F0"


def build_risk_heatmap(
    record: AttackPathRecord,
    components: list[dict],
) -> go.Figure:
    """
    Component × Risk Level heatmap.
    Rows = detected components, Columns = High / Medium / Low,
    Cell value = count of attack paths at that risk level touching
    that component.
    """
    comp_types = list({
        c.get("component_type", "Unknown") for c in components
    })
    risk_levels = ["High", "Medium", "Low"]

    # Build count matrix
    matrix: dict[str, dict[str, int]] = {
        ct: {rl: 0 for rl in risk_levels} for ct in comp_types
    }

    for path in record.attack_paths:
        for comp in components:
            ct = comp.get("component_type", "Unknown")
            if ct in matrix:
                matrix[ct][path.risk_level] = (
                    matrix[ct].get(path.risk_level, 0) + 1
                )

    z_vals, text_vals = [], []
    for ct in comp_types:
        row_z, row_t = [], []
        for rl in risk_levels:
            count = matrix[ct][rl]
            row_z.append(_RISK_NUMERIC[rl] if count > 0 else 0)
            row_t.append(str(count) if count > 0 else "0")
        z_vals.append(row_z)
        text_vals.append(row_t)

    fig = go.Figure(data=go.Heatmap(
        z=z_vals,
        x=risk_levels,
        y=comp_types,
        text=text_vals,
        texttemplate="%{text}",
        colorscale=[
            [0.0,  "#1E3A5F"],
            [0.33, "#10B981"],
            [0.66, "#F59E0B"],
            [1.0,  "#EF4444"],
        ],
        showscale=False,
        hoverongaps=False,
        hovertemplate="Component: %{y}<br>Risk Level: %{x}<br>Path Count: %{text}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Component × Risk Level", font=dict(color=_TEXT, size=15)),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        font=dict(color=_TEXT, family="Segoe UI"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title="Risk Level", color=_TEXT, gridcolor="#1E3A5F"),
        yaxis=dict(title="Component",  color=_TEXT, gridcolor="#1E3A5F"),
        height=350,
    )
    return fig


def build_path_score_chart(record: AttackPathRecord) -> go.Figure:
    """
    Horizontal bar chart showing risk score per attack path,
    coloured by risk level.
    """
    paths = sorted(record.attack_paths, key=lambda p: p.risk_score, reverse=True)

    names  = [p.name[:40] + ("..." if len(p.name) > 40 else "") for p in paths]
    scores = [p.risk_score for p in paths]
    colors = [_RISK_COLORS.get(p.risk_level, "#94A3B8") for p in paths]

    fig = go.Figure(go.Bar(
        x=scores,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Risk Score: %{x:.1f}/100<extra></extra>",
    ))

    fig.add_vline(x=61, line_dash="dash", line_color="#EF4444",
                  annotation_text="High threshold", annotation_font_color="#EF4444")
    fig.add_vline(x=31, line_dash="dash", line_color="#F59E0B",
                  annotation_text="Medium threshold", annotation_font_color="#F59E0B")

    fig.update_layout(
        title=dict(text="Risk Score per Attack Path", font=dict(color=_TEXT, size=15)),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        font=dict(color=_TEXT, family="Segoe UI"),
        margin=dict(l=20, r=80, t=50, b=20),
        xaxis=dict(title="Risk Score (0–100)", range=[0, 110],
                   color=_TEXT, gridcolor="#1E3A5F"),
        yaxis=dict(color=_TEXT),
        height=max(250, len(paths) * 55),
    )
    return fig


def build_lia_chart(record: AttackPathRecord) -> go.Figure:
    """
    Grouped bar chart showing average Likelihood, Impact and
    Exposure per attack path — helps spot which dimension drives
    the risk score.
    """
    paths = sorted(record.attack_paths, key=lambda p: p.risk_score, reverse=True)
    names = [p.path_id for p in paths]

    fig = go.Figure()
    for metric, color in [
        ("likelihood", "#00B4D8"),
        ("impact",     "#EF4444"),
        ("exposure",   "#F59E0B"),
    ]:
        fig.add_trace(go.Bar(
            name=metric.capitalize(),
            x=names,
            y=[getattr(p, metric) for p in paths],
            marker_color=color,
            hovertemplate=f"{metric.capitalize()}: %{{y:.1f}}<extra></extra>",
        ))

    fig.update_layout(
        barmode="group",
        title=dict(text="Likelihood · Impact · Exposure per Path",
                   font=dict(color=_TEXT, size=15)),
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        font=dict(color=_TEXT, family="Segoe UI"),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title="Attack Path", color=_TEXT, gridcolor="#1E3A5F"),
        yaxis=dict(title="Score (0–10)", range=[0, 11],
                   color=_TEXT, gridcolor="#1E3A5F"),
        legend=dict(bgcolor="#0D1B2A", bordercolor="#1E3A5F"),
        height=350,
    )
    return fig


def build_risk_gauge(overall_score: float, risk_level: str) -> go.Figure:
    """
    Gauge chart showing the overall security score (0–100).
    """
    color = _RISK_COLORS.get(risk_level, "#94A3B8")

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=overall_score,
        delta={"reference": 50, "valueformat": ".1f"},
        title={"text": f"Overall Security Score<br><span style='font-size:0.8em;color:{color}'>{risk_level} Risk</span>",
               "font": {"color": _TEXT, "size": 14}},
        number={"font": {"color": color, "size": 36}, "suffix": "/100"},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": _TEXT,
                     "tickfont": {"color": _TEXT}},
            "bar":  {"color": color},
            "bgcolor": _BG,
            "bordercolor": "#1E3A5F",
            "steps": [
                {"range": [0,  30], "color": "#0A2510"},
                {"range": [30, 61], "color": "#2A1A05"},
                {"range": [61, 100],"color": "#2A0505"},
            ],
            "threshold": {
                "line": {"color": color, "width": 4},
                "thickness": 0.75,
                "value": overall_score,
            },
        },
    ))

    fig.update_layout(
        paper_bgcolor=_PAPER,
        font=dict(color=_TEXT, family="Segoe UI"),
        margin=dict(l=20, r=20, t=60, b=20),
        height=280,
    )
    return fig