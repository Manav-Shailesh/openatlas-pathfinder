"""
AI-powered risk scoring for each attack path.
Gemini provides context-aware scores AND written explanations —
something a pure formula (L × I × E) can never produce.
"""

import json
import re

import google.generativeai as genai

from app.config import settings
from app.db.schemas import AttackPath

_RISK_PROMPT = """
You are a cybersecurity risk analyst specializing in AI system threats.

Score the following attack path for an AI system with these components:
{components}

ATTACK PATH:
Name: {path_name}
Entry Point: {entry_point}
Steps:
{steps}
Final Impact: {final_impact}

Provide:
1. likelihood (1-10): how easy is this attack to execute in practice
2. impact (1-10): how severe is the business damage if successful
3. exposure (1-10): how exposed is this specific architecture to this path
4. explanation: 2-3 sentences explaining the score specific to THIS architecture

Return ONLY this JSON, no markdown, no explanation outside JSON:
{{
  "likelihood": 7,
  "impact": 8,
  "exposure": 6,
  "explanation": "Your specific explanation here referencing the architecture components."
}}
"""

_RISK_THRESHOLDS = {
    "High":   61,
    "Medium": 31,
    "Low":    0,
}


def _formula_score(likelihood: float, impact: float, exposure: float) -> float:
    """
    Risk = (Likelihood × Impact × Exposure) / 10
    Normalised to 0-100 range.
    """
    raw = (likelihood * impact * exposure) / 10
    return round(min(raw, 100.0), 1)


def _risk_level(score: float) -> str:
    if score >= 61:
        return "High"
    elif score >= 31:
        return "Medium"
    return "Low"


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    return text.strip()


def score_attack_path(
    path: AttackPath,
    components: list[dict],
) -> AttackPath:
    """
    Uses Gemini to score a single attack path with context-aware
    scores and a written explanation. Falls back to formula-only
    scoring if the API call fails.
    """
    if not settings.GOOGLE_API_KEY:
        score = _formula_score(path.likelihood, path.impact, path.exposure)
        path.risk_score = score
        path.risk_level = _risk_level(score)
        path.ai_explanation = "AI explanation unavailable — GOOGLE_API_KEY not set."
        return path

    components_text = ", ".join([
        c.get("component_type", c.get("name", "Unknown"))
        for c in components
    ])

    steps_text = "\n".join([
        f"  Step {s.step}: [{s.technique_id}] {s.technique_name} — {s.action}"
        for s in path.steps
    ])

    prompt = _RISK_PROMPT.format(
        components=components_text,
        path_name=path.name,
        entry_point=path.entry_point,
        steps=steps_text,
        final_impact=path.final_impact,
    )

    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
            ),
        )
        cleaned = _clean_json(response.text)
        data = json.loads(cleaned)

        path.likelihood = float(data.get("likelihood", path.likelihood))
        path.impact = float(data.get("impact", path.impact))
        path.exposure = float(data.get("exposure", 5.0))
        path.ai_explanation = data.get("explanation", "")

    except Exception as e:
        print(f"[risk_scorer] Gemini scoring failed for {path.path_id}: {e}")
        path.ai_explanation = "AI explanation unavailable — scored using formula only."

    # Always apply formula to get final score
    path.risk_score = _formula_score(path.likelihood, path.impact, path.exposure)
    path.risk_level = _risk_level(path.risk_score)
    return path


def score_all_paths(
    paths: list[AttackPath],
    components: list[dict],
) -> list[AttackPath]:
    """Scores every attack path and returns them sorted by risk score."""
    scored = [score_attack_path(p, components) for p in paths]
    scored.sort(key=lambda p: p.risk_score, reverse=True)
    return scored