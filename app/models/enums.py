"""
Shared enums used across ingestion, mapping, attack-path, and scoring
modules. Centralizing these avoids typo'd string literals like
"llm" vs "LLM" vs "Llm" scattered across the codebase.
"""

from enum import Enum


class ComponentType(str, Enum):
    LLM = "LLM"
    RAG = "RAG"
    VECTOR_DB = "Vector Database"
    AGENT = "Agent"
    TOOL_CALLING = "Tool Calling"
    MEMORY = "Memory"
    EXTERNAL_API = "External API"
    PLUGIN = "Plugin"
    MCP = "MCP"
    KNOWLEDGE_BASE = "Knowledge Base"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    ANALYZED = "analyzed"
    FAILED = "failed"