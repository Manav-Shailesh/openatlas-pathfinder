"""
Core AI engine — sends detected components + mapped ATLAS techniques
to Gemini and asks it to reason about realistic attack chains.

This is the heart of Phase 5. Gemini generates novel, architecture-
specific multi-step attack paths that no hardcoded rule table could
produce. Every path is then validated against the local ATLAS knowledge
base to eliminate hallucinated technique IDs.
"""

import json
import re
from typing import Optional

import google.generativeai as genai

from app.config import settings
from app.atlas_mapping.atlas_loader import get_kb
from app.atlas_mapping.mapper import MappedTechnique
from app.db.schemas import AttackPath, AttackStep

# ── Prompt template ──────────────────────────────────────────────────────────

_ATTACK_PATH_PROMPT = """
You are a senior AI red team expert and MITRE ATLAS specialist.
Your job is to generate REALISTIC, SPECIFIC attack paths for the AI 
system architecture described below.

DETECTED ARCHITECTURE COMPONENTS:
{components}

MAPPED MITRE ATLAS TECHNIQUES:
{techniques}

YOUR TASK:
Generate 3 to 5 realistic multi-step attack paths that an adversary 
would actually use against THIS specific architecture.

STRICT RULES:
1. Every technique_id MUST be a real MITRE ATLAS ID from the list above
2. Each path must have between 3 and 6 steps
3. Steps must flow logically — each step enables the next
4. Paths must be SPECIFIC to this architecture — not generic
5. Different paths must use different entry points or attack strategies
6. sophistication must be exactly: "Low", "Medium", or "High"

Return ONLY this exact JSON structure, no explanation, no markdown:
{{
  "attack_paths": [
    {{
      "path_id": "PATH-001",
      "name": "Short descriptive name of this attack",
      "entry_point": "Where and how the attacker begins",
      "steps": [
        {{
          "step": 1,
          "technique_id": "AML.T0051",
          "technique_name": "LLM Prompt Injection",
          "action": "Specific thing the attacker does in this step",
          "leads_to": "What this step enables or unlocks for the attacker"
        }}
      ],
      "final_impact": "The business impact when this path succeeds",
      "likelihood": 7,
      "impact": 8,
      "sophistication": "Low"
    }}
  ]
}}
"""

# ── Validation helpers ───────────────────────────────────────────────────────

def _clean_json_response(text: str) -> str:
    """Strip markdown fences if Gemini wraps output despite instructions."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    return text.strip()


def _validate_and_filter_steps(
    steps: list[dict],
    valid_technique_ids: set[str],
) -> list[AttackStep]:
    """
    Removes any step whose technique_id is not in the real ATLAS KB.
    This is the hallucination guard — Gemini sometimes invents IDs.
    """
    valid_steps = []
    for step_data in steps:
        tid = step_data.get("technique_id", "")
        if tid not in valid_technique_ids:
            # Skip hallucinated technique IDs silently
            continue
        try:
            valid_steps.append(AttackStep(
                step=step_data.get("step", len(valid_steps) + 1),
                technique_id=tid,
                technique_name=step_data.get("technique_name", ""),
                action=step_data.get("action", ""),
                leads_to=step_data.get("leads_to", ""),
            ))
        except Exception:
            continue
    # Renumber steps after filtering
    for i, s in enumerate(valid_steps):
        s.step = i + 1
    return valid_steps


def _build_fallback_paths(
    mapped_techniques: list[MappedTechnique],
) -> list[AttackPath]:
    """
    Rule-based fallback used ONLY when Gemini returns nothing usable.
    Builds basic 3-step paths from the highest-confidence techniques.
    """
    if len(mapped_techniques) < 3:
        return []

    top = mapped_techniques[:6]

    # Group by tactic
    execution = [t for t in top if t.tactic_name and "Execution" in t.tactic_name]
    persistence = [t for t in top if t.tactic_name and "Persistence" in t.tactic_name]
    exfil = [t for t in top if t.tactic_name and "Exfiltration" in t.tactic_name]
    impact = [t for t in top if t.tactic_name and "Impact" in t.tactic_name]

    paths = []
    step_pool = execution + persistence + exfil + impact

    if len(step_pool) >= 3:
        steps = [
            AttackStep(step=i+1, technique_id=t.technique_id,
                      technique_name=t.technique_name,
                      action=f"Adversary executes {t.technique_name}",
                      leads_to="Enables next attack step")
            for i, t in enumerate(step_pool[:4])
        ]
        paths.append(AttackPath(
            path_id="PATH-FALLBACK-001",
            name="Fallback: Sequential Technique Chain",
            entry_point="Initial access to AI system",
            steps=steps,
            final_impact="System compromise via chained techniques",
            likelihood=5.0,
            impact=5.0,
            exposure=5.0,
        ))

    return paths


# ── Main generator ───────────────────────────────────────────────────────────

def generate_attack_paths(
    components: list[dict],
    mapped_techniques: list[MappedTechnique],
) -> list[AttackPath]:
    """
    Main entry point.
    1. Sends components + techniques to Gemini
    2. Parses and validates the response
    3. Falls back to rule-based paths if needed
    """
    if not settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY not set. Add it to .env to enable "
            "AI-powered attack path generation."
        )

    if not mapped_techniques:
        return []

    kb = get_kb()
    valid_technique_ids = set(kb.techniques.keys())

    # Build prompt context
    components_text = "\n".join([
        f"- {c.get('component_type', c.get('name', 'Unknown'))} "
        f"(confidence: {c.get('confidence', 0):.2f})"
        for c in components
    ])

    techniques_text = "\n".join([
        f"- {t.technique_id}: {t.technique_name} "
        f"[Tactic: {t.tactic_name or 'Unknown'}]"
        for t in mapped_techniques[:20]  # cap to avoid token overflow
    ])

    prompt = _ATTACK_PATH_PROMPT.format(
        components=components_text,
        techniques=techniques_text,
    )

    # Call Gemini
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.4,
                max_output_tokens=4096,
            ),
        )
        raw_text = response.text
    except Exception as e:
        print(f"[ai_path_generator] Gemini API error: {e}")
        return _build_fallback_paths(mapped_techniques)

    # Parse response
    cleaned = _clean_json_response(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[ai_path_generator] JSON parse error: {e}\nRaw: {raw_text[:300]}")
        return _build_fallback_paths(mapped_techniques)

    raw_paths = parsed.get("attack_paths", [])
    if not raw_paths:
        print("[ai_path_generator] Gemini returned empty paths, using fallback")
        return _build_fallback_paths(mapped_techniques)

    # Build and validate AttackPath objects
    attack_paths: list[AttackPath] = []
    for i, p in enumerate(raw_paths):
        raw_steps = p.get("steps", [])
        valid_steps = _validate_and_filter_steps(raw_steps, valid_technique_ids)

        # Discard paths with fewer than 2 valid steps
        if len(valid_steps) < 2:
            print(f"[ai_path_generator] PATH-{i+1} discarded — too few valid steps after validation")
            continue

        try:
            path = AttackPath(
                path_id=p.get("path_id", f"PATH-{i+1:03d}"),
                name=p.get("name", f"Attack Path {i+1}"),
                entry_point=p.get("entry_point", "Unknown entry point"),
                steps=valid_steps,
                final_impact=p.get("final_impact", "Unknown impact"),
                likelihood=float(p.get("likelihood", 5)),
                impact=float(p.get("impact", 5)),
                exposure=5.0,  # default, overridden by risk_scorer
            )
            attack_paths.append(path)
        except Exception as e:
            print(f"[ai_path_generator] Failed to build path {i}: {e}")
            continue

    if not attack_paths:
        print("[ai_path_generator] All paths failed validation, using fallback")
        return _build_fallback_paths(mapped_techniques)

    print(f"[ai_path_generator] Generated {len(attack_paths)} valid attack paths")
    return attack_paths