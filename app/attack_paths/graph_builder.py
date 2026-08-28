"""
Builds NetworkX directed graphs from AI-generated attack paths.
Each node is a technique, each edge is a step transition.
PyVis converts the NetworkX graph to an interactive HTML visualization.
"""

import networkx as nx
from pyvis.network import Network
from pathlib import Path
import tempfile

from app.db.schemas import AttackPath

# Risk level colours for nodes
_RISK_COLORS = {
    "High":    "#EF4444",
    "Medium":  "#F59E0B",
    "Low":     "#10B981",
    "Unknown": "#94A3B8",
}

_TACTIC_COLORS = {
    "Execution":         "#7C3AED",
    "Persistence":       "#F59E0B",
    "Exfiltration":      "#EF4444",
    "Impact":            "#DC2626",
    "Defense Evasion":   "#0891B2",
    "Discovery":         "#059669",
    "Collection":        "#D97706",
    "Initial Access":    "#2563EB",
    "Privilege Escalation": "#7C2D12",
}


def build_attack_graph(attack_paths: list[AttackPath]) -> nx.DiGraph:
    """
    Builds a directed graph where:
    - Nodes = ATLAS techniques (shared across paths)
    - Edges = technique → technique transitions
    - Edge labels = path name
    """
    G = nx.DiGraph()

    for path in attack_paths:
        for step in path.steps:
            # Add node if not already present
            if step.technique_id not in G.nodes:
                G.add_node(
                    step.technique_id,
                    label=f"{step.technique_id}\n{step.technique_name}",
                    technique_name=step.technique_name,
                    action=step.action,
                    title=f"{step.technique_name}\n\n{step.action}",
                )

        # Add edges between consecutive steps
        for i in range(len(path.steps) - 1):
            src = path.steps[i].technique_id
            dst = path.steps[i + 1].technique_id
            G.add_edge(
                src, dst,
                path_id=path.path_id,
                path_name=path.name,
                risk_level=path.risk_level,
                weight=path.risk_score,
            )

    return G


def build_pyvis_html(
    attack_paths: list[AttackPath],
    height: str = "600px",
) -> str:
    """
    Converts attack paths to an interactive PyVis HTML graph.
    Returns the HTML as a string for embedding in Streamlit.
    """
    G = build_attack_graph(attack_paths)

    net = Network(
        height=height,
        width="100%",
        bgcolor="#0D1B2A",
        font_color="#FFFFFF",
        directed=True,
    )
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=200)

    # Add nodes
    for node_id, attrs in G.nodes(data=True):
        net.add_node(
            node_id,
            label=attrs.get("label", node_id),
            title=attrs.get("title", node_id),
            color="#00B4D8",
            size=25,
            font={"size": 10, "color": "#FFFFFF"},
            borderWidth=2,
            borderWidthSelected=4,
        )

    # Add edges with path colour by risk level
    for src, dst, attrs in G.edges(data=True):
        risk_color = _RISK_COLORS.get(attrs.get("risk_level", "Unknown"), "#94A3B8")
        net.add_edge(
            src, dst,
            title=attrs.get("path_name", ""),
            color=risk_color,
            width=2,
            arrows="to",
        )

    # Disable physics controls in output for cleaner look
    net.set_options("""
    {
      "interaction": {
        "hover": true,
        "tooltipDelay": 100
      },
      "edges": {
        "smooth": {
          "type": "curvedCW",
          "roundness": 0.2
        }
      }
    }
    """)

    # Write to temp file and read back as string
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        net.save_graph(f.name)
        tmp_path = f.name

    with open(tmp_path, "r", encoding="utf-8") as f:
        html = f.read()

    Path(tmp_path).unlink(missing_ok=True)
    return html


def get_graph_stats(G: nx.DiGraph) -> dict:
    """Returns summary statistics about the attack graph."""
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "unique_techniques": list(G.nodes()),
        "most_connected_technique": (
            max(G.nodes(), key=lambda n: G.degree(n))
            if G.nodes() else None
        ),
    }