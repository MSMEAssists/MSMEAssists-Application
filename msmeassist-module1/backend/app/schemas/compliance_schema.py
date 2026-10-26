"""
Pydantic schemas for the Scheme Compliance Agent.

Verdict per rule:
  MET         — profile fact confirms the rule from official evidence
  NOT_MET     — profile fact explicitly conflicts with the rule
  NEEDS_INFO  — rule found but profile field is missing/ambiguous

Gap analysis:
  GapItem     — one specific named requirement for the scheme
  gap_analysis— the "you have / you are missing" checklist at the top
"""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RuleVerdict(str, Enum):
    MET        = "met"
    NOT_MET    = "not_met"
    NEEDS_INFO = "needs_info"


class OverallComplianceStatus(str, Enum):
    READY             = "ready"
    PARTIALLY_READY   = "partially_ready"
    ACTION_REQUIRED   = "action_required"
    INSUFFICIENT_DATA = "insufficient_data"


# ---------------------------------------------------------------------------
# Gap Analysis — the clear "you have / you are missing" checklist
# ---------------------------------------------------------------------------

class GapItem(BaseModel):
    requirement: str          = Field(description="Short name of the requirement, e.g. 'Udyam Registration'")
    description: str          = Field(description="One-line description of what is required")
    status: RuleVerdict                          # met / not_met / needs_info
    profile_value: Optional[str] = None          # what the profile shows for this requirement
    gap_detail: Optional[str]   = None           # what is missing or what action to take
    how_to_fix: Optional[str]   = None           # specific step-by-step fix


# ---------------------------------------------------------------------------
# Per-rule result (from RAG extraction)
# ---------------------------------------------------------------------------

class ComplianceRuleResult(BaseModel):
    rule_id: str
    category: str
    rule_statement: str
    verdict: RuleVerdict
    profile_fact: Optional[str]  = None
    explanation: str
    source_chunk_id:     Optional[str] = None
    source_page_number:  Optional[int] = None
    source_organization: Optional[str] = None
    source_url:          Optional[str] = None


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class SchemeComplianceRequest(BaseModel):
    scheme_id:           str
    scheme_name:         str
    scheme_organization: Optional[str] = None
    official_url:        Optional[str] = None
    knowledge_type:      Optional[str] = Field(default="SCHEME")
    # Fix 1 — document-level pinning
    document_id:         Optional[str] = Field(default=None)
    source_id:           Optional[str] = Field(default=None)


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class SchemeComplianceResponse(BaseModel):
    scheme_name:         str
    scheme_organization: str
    official_url:        Optional[str] = None
    business_name:       str
    msme_classification: str

    overall_status:  OverallComplianceStatus
    overall_summary: str

    # Gap analysis — the clear checklist shown at the top
    gap_analysis:     List[GapItem] = Field(default_factory=list)
    gap_met_count:    int = 0
    gap_missing_count: int = 0

    # RAG-extracted rules — the evidence-backed detail
    rules:            List[ComplianceRuleResult]
    total_rules:      int
    met_count:        int
    not_met_count:    int
    needs_info_count: int

    rag_chunks_used:   int           = 0
    rag_evidence_note: Optional[str] = None
    used_fallback:     bool          = False   # True when scheme-specific templates were used

    disclaimer: str = Field(
        default=(
            "This compliance assessment is for guidance only. "
            "Final eligibility, sanctioned benefits, and approval decisions are made solely "
            "by the respective government authority or implementing agency. "
            "Always verify requirements from the official scheme portal before applying."
        )
    )
