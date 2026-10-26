"""
Export Agent Schemas

Pydantic data models for export readiness assessment, DGFT/RoDTEP scheme eligibility,
license verification, customs document checklists, and export advisory.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    product_category: Optional[str] = Field(
        None, description="Product category or HS code description (e.g. Processed Food, Textiles, Engineering)"
    )
    target_country: Optional[str] = Field(
        None, description="Target export destination country (e.g. UAE, USA, Germany, Australia)"
    )
    estimated_export_turnover_inr: Optional[float] = Field(
        None, description="Estimated annual export turnover in INR"
    )
    has_iec: Optional[bool] = Field(None, description="User override for Import Export Code")
    has_rcmc: Optional[bool] = Field(None, description="User override for RCMC registration")


class ExportReadinessScore(BaseModel):
    score: int = Field(..., description="Export readiness score from 0 to 100")
    level: str = Field(..., description="Level: High Readiness, Moderate Readiness, or Beginning Journey")
    summary: str = Field(..., description="Executive summary of readiness")
    strengths: List[str] = Field(default_factory=list, description="Key enterprise advantages")
    gaps: List[str] = Field(default_factory=list, description="Key readiness gaps")


class ExportSchemeItem(BaseModel):
    id: str
    title: str
    organization: str
    category: str
    benefit_description: str
    estimated_benefit: str
    eligibility_status: str  # "eligible" | "action_needed" | "info_needed"
    official_url: str
    what_to_do: Optional[str] = None


class LicenseAuditItem(BaseModel):
    name: str
    authority: str
    status: str  # "met" | "missing" | "needs_verification"
    profile_value: Optional[str] = None
    description: str
    how_to_fix: str
    portal_url: Optional[str] = None


class DocumentChecklistItem(BaseModel):
    document_name: str
    stage: str  # "Pre-Shipment" | "Customs Clearance" | "Post-Shipment"
    mandatory: bool
    status: str  # "ready" | "pending"
    description: str


class ExportAdvisoryResponse(BaseModel):
    business_name: str
    msme_classification: str
    industry: Optional[str] = None
    state: Optional[str] = None
    readiness: ExportReadinessScore
    schemes: List[ExportSchemeItem]
    licenses: List[LicenseAuditItem]
    documents: List[DocumentChecklistItem]
    disclaimer: str
    official_portals: List[Dict[str, str]]
