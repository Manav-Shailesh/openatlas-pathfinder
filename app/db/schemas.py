"""
Pydantic schemas describing the shape of documents stored in MongoDB.
MongoDB itself enforces no schema, so these models are our contract —
validate data against them before inserting, and parse data through
them after reading.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ArchitectureComponent(BaseModel):
    """A single detected AI component (e.g. LLM, RAG, Tool Calling)."""
    name: str
    component_type: str        # will become an enum in Phase 1 Step 9
    confidence: float = Field(ge=0.0, le=1.0)
    source_text: Optional[str] = None

class AnalysisRecord(BaseModel):
    """
    Top-level record for one user analysis session —
    one uploaded document/architecture = one AnalysisRecord.
    """
    analysis_id: str
    filename: Optional[str] = None
    raw_text: Optional[str] = None
    components: List[ArchitectureComponent] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"   # pending | analyzed | failed

class HealthCheckRecord(BaseModel):
    """Tiny record used only to verify DB read/write works (Phase 1 test)."""
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    ok: bool

class TechniqueMapping(BaseModel):
    """One matched ATLAS technique, with the component(s) that triggered it."""
    technique_id: str
    technique_name: str
    tactic_id: Optional[str] = None
    tactic_name: str
    maturity: Optional[str] = None
    url: str
    matched_components: List[str] = []

class AtlasMappingRecord(BaseModel):
    """Result of running Phase 4 mapping against one AnalysisRecord."""
    mapping_id: str
    analysis_id: str
    techniques: List[TechniqueMapping] = []
    tactic_summary: dict = {}   # {"Execution": 3, "Persistence": 2, ...}
    created_at: datetime = Field(default_factory=datetime.utcnow)