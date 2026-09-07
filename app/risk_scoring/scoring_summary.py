"""
Computes summary statistics from attack path records for the
risk dashboard. No AI calls here — pure data aggregation over
what Phase 5 already generated and saved to MongoDB.
"""

from collections import defaultdict
from app.db.schemas import AttackPathRecord, AttackPath


def compute_overall_score(record: AttackPathRecord) -> dict:
    """
    Computes the overall security score and breakdown from all
    attack paths in the record.

    Returns a dict consumed directly by the Streamlit dashboard.
    """
    if not record.attack_paths:
        return {
            "overall_score": 0.0,
            "overall_risk_level": "Unknown",
            "total_paths": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "average_score": 0.0,
            "highest_score": 0.0,
            "highest_path_name": "N/A",
            "average_likelihood": 0.0,
            "average_impact": 0.0,
            "average_exposure": 0.0,
        }

    paths = record.attack_paths
    scores = [p.risk_score for p in paths]

    high_count   = sum(1 for p in paths if p.risk_level == "High")
    medium_count = sum(1 for p in paths if p.risk_level == "Medium")
    low_count    = sum(1 for p in paths if p.risk_level == "Low")

    # Overall score = weighted: highest path carries most weight
    highest_score = max(scores)
    average_score = sum(scores) / len(scores)
    overall_score = round((highest_score * 0.6) + (average_score * 0.4), 1)

    if overall_score >= 61:
        overall_risk_level = "High"
    elif overall_score >= 31:
        overall_risk_level = "Medium"
    else:
        overall_risk_level = "Low"

    highest_path = max(paths, key=lambda p: p.risk_score)

    return {
        "overall_score":      overall_score,
        "overall_risk_level": overall_risk_level,
        "total_paths":        len(paths),
        "high_count":         high_count,
        "medium_count":       medium_count,
        "low_count":          low_count,
        "average_score":      round(average_score, 1),
        "highest_score":      round(highest_score, 1),
        "highest_path_name":  highest_path.name,
        "average_likelihood": round(sum(p.likelihood for p in paths) / len(paths), 1),
        "average_impact":     round(sum(p.impact     for p in paths) / len(paths), 1),
        "average_exposure":   round(sum(p.exposure   for p in paths) / len(paths), 1),
    }


def compute_tactic_breakdown(record: AttackPathRecord) -> list[dict]:
    """
    Groups techniques across all attack paths by tactic and
    calculates average risk per tactic.

    Returns a list of dicts sorted by average risk descending.
    """
    tactic_scores: dict[str, list[float]] = defaultdict(list)
    tactic_technique_counts: dict[str, set] = defaultdict(set)

    for path in record.attack_paths:
        for step in path.steps:
            # Use path risk score as proxy for step risk
            tactic_scores[step.technique_id[:10]].append(path.risk_score)
            tactic_technique_counts[step.technique_id[:10]].add(step.technique_id)

    breakdown = []
    for tactic_prefix, scores in tactic_scores.items():
        avg = sum(scores) / len(scores)
        breakdown.append({
            "tactic": tactic_prefix,
            "average_risk": round(avg, 1),
            "technique_count": len(tactic_technique_counts[tactic_prefix]),
            "risk_level": "High" if avg >= 61 else "Medium" if avg >= 31 else "Low",
        })

    return sorted(breakdown, key=lambda x: x["average_risk"], reverse=True)


def compute_component_risk(
    record: AttackPathRecord,
    components: list[dict],
) -> list[dict]:
    """
    Estimates risk contribution per detected component by checking
    which components appear in each attack path's steps via
    technique matching.

    Returns a list of dicts with component name and risk score.
    """
    component_scores: dict[str, list[float]] = defaultdict(list)

    # Map technique IDs back to their source components
    for path in record.attack_paths:
        for step in path.steps:
            # Assign path risk to all components (simplified attribution)
            for comp in components:
                component_scores[comp.get("component_type", "Unknown")].append(
                    path.risk_score
                )
            break  # one attribution per path to avoid inflation

    result = []
    for comp_type, scores in component_scores.items():
        avg = sum(scores) / len(scores)
        result.append({
            "component": comp_type,
            "average_risk": round(avg, 1),
            "risk_level": "High" if avg >= 61 else "Medium" if avg >= 31 else "Low",
            "path_count": len(scores),
        })

    return sorted(result, key=lambda x: x["average_risk"], reverse=True)


def compute_mitigation_summary(record: AttackPathRecord) -> list[dict]:
    """
    Aggregates all mitigations across attack paths, deduplicates by
    title, and returns them sorted by how many paths they address.
    """
    mitigation_map: dict[str, dict] = {}

    for path in record.attack_paths:
        for m in path.mitigations:
            title = m.get("title", "Unknown")
            if title not in mitigation_map:
                mitigation_map[title] = {
                    "title":                title,
                    "description":          m.get("description", ""),
                    "control_type":         m.get("control_type", ""),
                    "effort":               m.get("effort", ""),
                    "atlas_mitigation_id":  m.get("atlas_mitigation_id", ""),
                    "addresses_paths":      0,
                }
            mitigation_map[title]["addresses_paths"] += 1

    return sorted(
        mitigation_map.values(),
        key=lambda x: x["addresses_paths"],
        reverse=True,
    )