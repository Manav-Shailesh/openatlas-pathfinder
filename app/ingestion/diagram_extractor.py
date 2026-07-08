"""
Diagram understanding using Google Gemini Vision (free tier).

Sends an architecture diagram image to Gemini and parses the response
into the same ArchitectureComponent structure used by text-based
detection. Everything downstream (Phase 3 onward) is unaware of
whether components came from text or image — it just sees the same
ArchitectureComponent list either way.
"""

import base64
import json
import re
from typing import Union, BinaryIO

import google.generativeai as genai
from PIL import Image
import io

from app.config import settings
from app.db.schemas import ArchitectureComponent
from app.models.enums import ComponentType

# All valid component type strings our system recognises
_VALID_TYPES = {c.value for c in ComponentType}

_EXTRACTION_PROMPT = f"""You are analyzing an AI system architecture diagram for a
defensive security threat-modeling tool.

Look carefully at all boxes, labels, arrows, icons, and annotations in this diagram.

Identify which of the following AI component types are visually present:
{", ".join(sorted(_VALID_TYPES))}

Return ONLY a valid JSON array. No explanation, no markdown fences, no preamble.

Each element in the array must have exactly these four fields:
- "component_type": must be one of the exact strings listed above
- "name": the label or text as it appears in the diagram (use component_type value if unlabeled)
- "confidence": float between 0.0 and 1.0 reflecting how clearly this component appears
- "source_text": brief description of where in the diagram you saw it

Only include components that are actually present. If nothing is detected, return: []

Example of correct output:
[
  {{"component_type": "LLM", "name": "GPT-4", "confidence": 0.95, "source_text": "central box labeled GPT-4"}},
  {{"component_type": "Tool Calling", "name": "Tool Calling", "confidence": 0.85, "source_text": "right side node connected to LLM"}}
]"""


def _media_type_for(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    raise ValueError(
        f"Unsupported image type: '{filename}'. "
        f"Supported formats: PNG, JPG, JPEG"
    )


def _read_bytes(file: Union[str, BinaryIO]) -> bytes:
    """Reads raw bytes from a file path or file-like object."""
    if hasattr(file, "read"):
        data = file.read()
        if hasattr(file, "seek"):
            file.seek(0)
        return data
    with open(file, "rb") as f:
        return f.read()


def _clean_json_response(text: str) -> str:
    """
    Strips markdown code fences if the model wraps its response in them
    despite being told not to. Defensive measure against model non-compliance.
    """
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text, flags=re.MULTILINE)
    text = re.sub(r"```$", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_components_from_diagram(
    filename: str,
    file: Union[str, BinaryIO],
) -> list[ArchitectureComponent]:
    """
    Sends a diagram image to Gemini Vision and returns a validated list
    of ArchitectureComponent objects.

    Returns an empty list if no known components are detected.
    Raises ValueError for unsupported file types or missing API key.
    Raises RuntimeError if the Gemini API call fails.
    """
    if not settings.GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/app/apikey "
            "and add it to your .env file."
        )

    # Validate file type before making any API call
    _media_type_for(filename)

    # Read image bytes and open with PIL (Gemini SDK accepts PIL images)
    image_bytes = _read_bytes(file)
    image = Image.open(io.BytesIO(image_bytes))

    # Configure Gemini
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)

    try:
        response = model.generate_content(
            [_EXTRACTION_PROMPT, image],
            generation_config=genai.GenerationConfig(
                temperature=0.1,      # low temp = more deterministic JSON output
                max_output_tokens=2048,
            ),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini API call failed: {e}") from e

    raw_text = response.text
    cleaned = _clean_json_response(raw_text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Could not parse Gemini response as JSON.\n"
            f"Error: {e}\n"
            f"Raw response: {raw_text}"
        )

    if not isinstance(parsed, list):
        raise ValueError(
            f"Expected a JSON array from Gemini, got: {type(parsed).__name__}"
        )

    components: list[ArchitectureComponent] = []
    for item in parsed:
        component_type = item.get("component_type", "")

        # Skip anything not in our known taxonomy
        # (model might hallucinate type names)
        if component_type not in _VALID_TYPES:
            continue

        try:
            components.append(
                ArchitectureComponent(
                    name=str(item.get("name", component_type)),
                    component_type=component_type,
                    confidence=float(item.get("confidence", 0.5)),
                    source_text=str(item.get("source_text", "")),
                )
            )
        except Exception:
            # Skip malformed items rather than crashing the whole pipeline
            continue

    return components