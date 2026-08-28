"""
Generates specific, actionable mitigations for each attack path
using Gemini. Mitigations are specific to THIS architecture and
THIS attack path — not generic security advice.
"""

import json
import re

import google.generativeai as genai

from app.config import settings
from app.db.schemas import AttackPath
from app.atlas_mapping.atlas_loader import get_kb

_MITIGATION_PROMPT = """
You are an AI security architect specializing in MITRE ATLAS mitigations.

Architecture components: {components}

Attack path to mitigate:
Name: {path_name}
Steps: {steps}
Final Impact: {final_impact}
Risk Level: {risk_level}

Generate 3 to 5 specific, actionable mitigations for THIS attack path.

Rules:
1. Each mitigation must be specific to this architecture — not generic
2. Reference the actual components (e.g. "the Gmail tool integration")
3. control_type must be exactly: "Preventive", "Detective", or "Corrective"
4. effort must be exactly: "Low", "Medium", or "High"

Return ONLY this JSON, no markdown:
{{
  "mitigations": [
    {{
      "title": "Short mitigation title",
      "description": "Specific action referencing this architecture",
      "control_type": "Preventive",
      "effort": "Medium",
      "atlas_mitigation_id": "AML.M0020"
    }}
  ]
}}
"""


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _get_fallback_mitigations(path: AttackPath) -> list[dict]:
    """Basic fallback mitigations from ATLAS knowledge base."""
    kb = get_kb()
    fallback_ids = ["AML.M0020", "AML.M0021", "AML.M0029"]
    mitigations = []
    for mid in fallback_ids:
        m = kb.mitigations.get(mid) if hasattr(kb, "mitigations") else None
        if m:
            mitigations.append({
                "title": m.get("name", mid),
                "description": m.get("description", "")[:200],
                "control_type": "Preventive",
                "effort": "Medium",
                "atlas_mitigation_id": mid,
            })
        else:
            mitigations.append({
                "title": f"Apply {mid}",
                "description": "Refer to MITRE ATLAS mitigation guidance.",
                "control_type": "Preventive",
                "effort": "Medium",
                "atlas_mitigation_id": mid,
            })
    return mitigations


def generate_mitigations_for_path(
    path: AttackPath,
    components: list[dict],
) -> AttackPath:
    """Generates AI mitigations for a single attack path."""
    if not settings.GOOGLE_API_KEY:
        path.mitigations = _get_fallback_mitigations(path)
        return path

    components_text = ", ".join([
        c.get("component_type", c.get("name", "Unknown"))
        for c in components
    ])

    steps_text = " → ".join([
        f"{s.technique_id} ({s.technique_name})"
        for s in path.steps
    ])

    prompt = _MITIGATION_PROMPT.format(
        components=components_text,
        path_name=path.name,
        steps=steps_text,
        final_impact=path.final_impact,
        risk_level=path.risk_level,
    )

    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )
        cleaned = _clean_json(response.text)
        data = json.loads(cleaned)
        path.mitigations = data.get("mitigations", [])

        if not path.mitigations:
            path.mitigations = _get_fallback_mitigations(path)

    except Exception as e:
        print(f"[mitigation_engine] Failed for {path.path_id}: {e}")
        path.mitigations = _get_fallback_mitigations(path)

    return path


def generate_all_mitigations(
    paths: list[AttackPath],
    components: list[dict],
) -> list[AttackPath]:
    """Generates mitigations for every attack path."""
    return [generate_mitigations_for_path(p, components) for p in paths]