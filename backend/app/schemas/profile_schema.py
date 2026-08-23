"""
Profile request/response schemas.

Response shapes here are the literal contract documented in
docs/module-1-api.md and docs/module-2-integration.md — do not change a
field name or remove a field without updating both docs in the same PR
(see docs/architecture.md §7, contract testing).
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    AreaType,
    BusinessType,
    MSMEClassification,
    PremisesType,
    ProfileStatus,
    ProfitabilityStatus,
    RegistrationStatus,
    RegistrationType,
    SocialCategory,
)
from app.utils.validators import is_valid_pin_code

# =====================================================================
# INPUT (request) schemas — one per section, all optional at the top
# level so POST /profile/me and PUT /profile/me can send partial bodies.
# =====================================================================


class BusinessSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: BusinessType
    industry: str
    sub_sector: Optional[str] = None
    established_date: date
    description: Optional[str] = None


class LocationSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str
    district: str
    city: str
    pin_code: str
    area_type: AreaType
    premises_type: Optional[PremisesType] = None

    @field_validator("pin_code")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not is_valid_pin_code(v):
            raise ValueError("pin_code must be exactly 6 digits")
        return v


class FinancialSectionIn(BaseModel):
    # extra="forbid" is what actually enforces "msme_classification is
    # never accepted from the client" — see docs/module-1-api.md PUT /profile/me.
    model_config = ConfigDict(extra="forbid")

    annual_turnover_inr: float = Field(ge=0)
    investment_inr: float = Field(ge=0)
    employee_count: int = Field(ge=0)
    has_existing_loan: Optional[bool] = None
    has_bank_finance: Optional[bool] = None
    profitability_status: Optional[ProfitabilityStatus] = None


class CharacteristicsSectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_women_owned: bool = False
    social_category: SocialCategory = SocialCategory.GENERAL
    is_first_gen_entrepreneur: bool = False
    is_startup_recognized: bool = False
    is_rural_enterprise: bool = False
    exports_currently: bool = False
    export_intent: bool = False
    is_tech_oriented: bool = False
    is_sustainable: bool = False


class RegistrationEntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RegistrationType
    status: RegistrationStatus
    identifier: Optional[str] = None  # raw value, write-only


class ProfileCreateRequest(BaseModel):
    """POST /api/profile/me — only `business` is required at creation."""

    model_config = ConfigDict(extra="forbid")

    business: BusinessSectionIn
    location: Optional[LocationSectionIn] = None
    financial: Optional[FinancialSectionIn] = None
    characteristics: Optional[CharacteristicsSectionIn] = None
    registrations: Optional[List[RegistrationEntryIn]] = None


class ProfileUpdateRequest(BaseModel):
    """PUT /api/profile/me — section-aware partial update."""

    model_config = ConfigDict(extra="forbid")

    business: Optional[BusinessSectionIn] = None
    location: Optional[LocationSectionIn] = None
    financial: Optional[FinancialSectionIn] = None
    characteristics: Optional[CharacteristicsSectionIn] = None
    registrations: Optional[List[RegistrationEntryIn]] = None


# =====================================================================
# OUTPUT (response) schemas — this is the Module 2 contract shape.
# =====================================================================


class BusinessSectionOut(BaseModel):
    name: str
    type: BusinessType
    industry: str
    sub_sector: Optional[str] = None
    established_date: date
    description: Optional[str] = None


class LocationSectionOut(BaseModel):
    state: str
    district: str
    city: str
    pin_code: str
    area_type: AreaType
    premises_type: Optional[PremisesType] = None


class FinancialSectionOut(BaseModel):
    annual_turnover_inr: float
    investment_inr: float
    employee_count: int
    has_existing_loan: Optional[bool] = None
    has_bank_finance: Optional[bool] = None
    profitability_status: Optional[ProfitabilityStatus] = None
    msme_classification: MSMEClassification


class CharacteristicsSectionOut(BaseModel):
    is_women_owned: bool
    social_category: SocialCategory
    is_first_gen_entrepreneur: bool
    is_startup_recognized: bool
    is_rural_enterprise: bool
    exports_currently: bool
    export_intent: bool
    is_tech_oriented: bool
    is_sustainable: bool


class RegistrationOut(BaseModel):
    type: RegistrationType
    status: RegistrationStatus
    masked_identifier: Optional[str] = None


class CompletenessOut(BaseModel):
    percentage: int
    sections: dict[str, bool]


class ProfileResponse(BaseModel):
    profile_id: str
    status: ProfileStatus
    business: Optional[BusinessSectionOut] = None
    location: Optional[LocationSectionOut] = None
    financial: Optional[FinancialSectionOut] = None
    characteristics: Optional[CharacteristicsSectionOut] = None
    registrations: List[RegistrationOut] = Field(default_factory=list)
    completeness: CompletenessOut
    updated_at: datetime


class MissingItem(BaseModel):
    section: str
    detail: str


class CompletenessResponse(BaseModel):
    percentage: int
    sections: dict[str, bool]
    missing: List[MissingItem] = Field(default_factory=list)


class EligibilityResponse(BaseModel):
    msme_classification: MSMEClassification
    attributes: List[str]
    computed_at: datetime
