"""
Mongo document shape for the `business_profiles` collection.

Nested sub-models mirror docs/architecture.md §3.2 exactly. All sections
are optional at the model level (profile is built incrementally across the
7-step wizard) — required-ness for a given wizard step is enforced by the
request schemas in app/schemas/profile_schema.py, not here.
"""
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

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
from app.utils.object_id import PyObjectId


class BusinessSection(BaseModel):
    """
    NOTE: established_date is stored as `datetime` (not `date`) because
    BSON/Mongo has no native date-only type — PyMongo/Motor cannot encode
    a bare `datetime.date`. The API contract still exposes `date` at the
    schema boundary (see schemas/profile_schema.py); the conversion happens
    in profile_service.py, not here.
    """

    name: str
    type: BusinessType
    industry: str
    sub_sector: Optional[str] = None
    established_date: datetime
    description: Optional[str] = None


class LocationSection(BaseModel):
    state: str
    district: str
    city: str
    pin_code: str
    area_type: AreaType
    premises_type: Optional[PremisesType] = None


class FinancialSection(BaseModel):
    annual_turnover_inr: float
    investment_inr: float
    employee_count: int
    has_existing_loan: Optional[bool] = None
    has_bank_finance: Optional[bool] = None
    profitability_status: Optional[ProfitabilityStatus] = None
    # Server-derived only — never accepted from client input (see profile_service.py)
    msme_classification: MSMEClassification = MSMEClassification.NOT_CLASSIFIED


class CharacteristicsSection(BaseModel):
    is_women_owned: bool = False
    social_category: SocialCategory = SocialCategory.GENERAL
    is_first_gen_entrepreneur: bool = False
    is_startup_recognized: bool = False
    is_rural_enterprise: bool = False
    exports_currently: bool = False
    export_intent: bool = False
    is_tech_oriented: bool = False
    is_sustainable: bool = False


class RegistrationEntry(BaseModel):
    type: RegistrationType
    status: RegistrationStatus
    identifier: Optional[str] = None  # raw value — write-only, never returned by API
    verified_at: Optional[datetime] = None


class CompletenessSnapshot(BaseModel):
    percentage: int = 0
    sections: dict[str, bool] = Field(default_factory=dict)


class ProfileModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    business: Optional[BusinessSection] = None
    location: Optional[LocationSection] = None
    financial: Optional[FinancialSection] = None
    characteristics: Optional[CharacteristicsSection] = CharacteristicsSection()
    registrations: List[RegistrationEntry] = Field(default_factory=list)
    completeness: CompletenessSnapshot = Field(default_factory=CompletenessSnapshot)
    status: ProfileStatus = ProfileStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
