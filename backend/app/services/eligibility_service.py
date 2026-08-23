"""
Eligibility engine.

Two responsibilities, both consumed via GET /api/profile/eligibility and
embedded in GET /api/profile/me (see docs/module-2-integration.md):

1. Derive `financial.msme_classification` from turnover/investment —
   always server-side, never accepted from the client (enforced by
   ProfileUpdateRequest/ProfileCreateRequest using extra="forbid").
2. Derive a flat, additive `attributes[]` tag list Module 2 can filter on
   without re-implementing this logic itself.

Thresholds below reflect the current Udyam classification bands (investment
in plant & machinery / equipment, and annual turnover). Kept as named
constants so they can be updated in one place if government thresholds
change.
"""
from datetime import datetime, timezone
from typing import List

from app.core.constants import MSMEClassification, RegistrationStatus
from app.models.profile_model import FinancialSection, ProfileModel
from app.schemas.profile_schema import EligibilityResponse

# Udyam classification thresholds (INR)
_MICRO_INVESTMENT_MAX = 1_00_00_000       # ₹1 crore
_MICRO_TURNOVER_MAX = 5_00_00_000         # ₹5 crore
_SMALL_INVESTMENT_MAX = 10_00_00_000      # ₹10 crore
_SMALL_TURNOVER_MAX = 50_00_00_000        # ₹50 crore
_MEDIUM_INVESTMENT_MAX = 50_00_00_000     # ₹50 crore
_MEDIUM_TURNOVER_MAX = 250_00_00_000      # ₹250 crore


def compute_msme_classification(financial: FinancialSection | None) -> MSMEClassification:
    if financial is None:
        return MSMEClassification.NOT_CLASSIFIED

    investment = financial.investment_inr
    turnover = financial.annual_turnover_inr

    if investment <= _MICRO_INVESTMENT_MAX and turnover <= _MICRO_TURNOVER_MAX:
        return MSMEClassification.MICRO
    if investment <= _SMALL_INVESTMENT_MAX and turnover <= _SMALL_TURNOVER_MAX:
        return MSMEClassification.SMALL
    if investment <= _MEDIUM_INVESTMENT_MAX and turnover <= _MEDIUM_TURNOVER_MAX:
        return MSMEClassification.MEDIUM
    return MSMEClassification.NOT_CLASSIFIED


def compute_attributes(profile: ProfileModel) -> List[str]:
    attributes: List[str] = []

    if profile.business:
        attributes.append(f"{profile.business.type.value}_sector")

    if profile.characteristics:
        c = profile.characteristics
        attributes.append(f"women_owned:{str(c.is_women_owned).lower()}")
        if c.social_category.value != "general":
            attributes.append(f"social_category:{c.social_category.value}")
        if c.is_first_gen_entrepreneur:
            attributes.append("first_generation_entrepreneur")
        if c.is_startup_recognized:
            attributes.append("startup_recognized")
        if c.is_rural_enterprise:
            attributes.append("rural_enterprise")
        if c.exports_currently:
            attributes.append("exports_currently")
        if c.export_intent:
            attributes.append("export_intent")
        if c.is_tech_oriented:
            attributes.append("technology_oriented")
        if c.is_sustainable:
            attributes.append("sustainable_practices")

    for reg in profile.registrations:
        if reg.status == RegistrationStatus.REGISTERED:
            attributes.append(f"{reg.type.value}_registered")
        elif reg.status == RegistrationStatus.NOT_REGISTERED:
            attributes.append(f"{reg.type.value}_missing")
        elif reg.status == RegistrationStatus.IN_PROGRESS:
            attributes.append(f"{reg.type.value}_in_progress")
        # not_applicable registrations are omitted — they carry no eligibility signal

    return attributes


def compute_eligibility(profile: ProfileModel) -> EligibilityResponse:
    classification = compute_msme_classification(profile.financial)
    attributes = compute_attributes(profile)
    return EligibilityResponse(
        msme_classification=classification,
        attributes=attributes,
        computed_at=datetime.now(timezone.utc),
    )
