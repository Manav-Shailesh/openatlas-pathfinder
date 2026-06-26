"""
Rule-based detection of AI architecture components from raw text.

This is deterministic keyword/synonym matching, not ML — appropriate
for Phase 2. Phase 3 (Architecture Understanding Engine) builds on
this output to construct the full architecture graph.
"""

import re
from typing import List

from app.models.enums import ComponentType
from app.db.schemas import ArchitectureComponent

# Maps each ComponentType to a list of regex-safe keyword/synonym patterns.
# Order doesn't matter; matching is case-insensitive.
COMPONENT_KEYWORDS: dict[ComponentType, list[str]] = {
    ComponentType.LLM: [
        r"gpt-?4", r"gpt-?3", r"llm", r"large language model",
        r"claude", r"gemini", r"llama", r"mistral",
    ],
    ComponentType.RAG: [
        r"\brag\b", r"retrieval[- ]augmented generation",
        r"retrieval augmented",
    ],
    ComponentType.VECTOR_DB: [
        r"pinecone", r"weaviate", r"chroma", r"qdrant", r"milvus",
        r"vector database", r"vector store", r"faiss",
    ],
    ComponentType.AGENT: [
        r"\bagent\b", r"autonomous agent", r"agentic",
    ],
    ComponentType.TOOL_CALLING: [
        r"tool calling", r"function calling", r"tool use",
    ],
    ComponentType.MEMORY: [
        r"agent memory", r"\bmemory\b", r"conversation history store",
    ],
    ComponentType.EXTERNAL_API: [
        r"gmail", r"slack", r"external api", r"third[- ]party api",
        r"\bapi integration\b",
    ],
    ComponentType.PLUGIN: [
        r"\bplugin\b", r"extension\b",
    ],
    ComponentType.MCP: [
        r"\bmcp\b", r"model context protocol",
    ],
    ComponentType.KNOWLEDGE_BASE: [
        r"knowledge base", r"\bkb\b", r"document store",
    ],
}


def detect_components(text: str) -> List[ArchitectureComponent]:
    """
    Scans `text` for known component keywords and returns one
    ArchitectureComponent per component type matched, including the
    snippet of text that triggered the match (for traceability).

    Confidence is currently a simple heuristic: more keyword matches
    for a given type = higher confidence, capped at 0.95.
    """
    detected: List[ArchitectureComponent] = []

    for component_type, patterns in COMPONENT_KEYWORDS.items():
        match_count = 0
        first_snippet = None

        for pattern in patterns:
            matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
            if matches:
                match_count += len(matches)
                if first_snippet is None:
                    start = max(matches[0].start() - 20, 0)
                    end = min(matches[0].end() + 20, len(text))
                    first_snippet = text[start:end].strip()

        if match_count > 0:
            confidence = min(0.5 + 0.15 * match_count, 0.95)
            detected.append(
                ArchitectureComponent(
                    name=component_type.value,
                    component_type=component_type.value,
                    confidence=round(confidence, 2),
                    source_text=first_snippet,
                )
            )

    return detected