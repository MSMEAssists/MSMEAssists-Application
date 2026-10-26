"""
Unit tests for Module 5: Agent Orchestration & Decision Intelligence.
"""
import pytest
from app.models.profile_model import (
    BusinessSection,
    CharacteristicsSection,
    FinancialSection,
    LocationSection,
    ProfileModel,
    RegistrationEntry,
)
from app.core.constants import (
    AreaType,
    BusinessType,
    MSMEClassification,
    RegistrationStatus,
    RegistrationType,
    SocialCategory,
)
from app.schemas.decision_intelligence_schema import (
    DecisionObjective,
    DecisionRequest,
)
from app.services.decision_intelligence_service import DecisionIntelligenceService
from app.services.permission_license_service import PermissionLicenseService
from app.utils.object_id import PyObjectId


def make_test_profile() -> ProfileModel:
    return ProfileModel(
        user_id=PyObjectId(),
        business=BusinessSection(
            name="Apex Precision Engineering",
            type=BusinessType.MANUFACTURING,
            industry="Fabrication & Machine Tools",
            sub_sector="Automotive Components",
            established_date="2021-04-15T00:00:00Z",
            description="Precision CNC milling and fabrication unit.",
        ),
        location=LocationSection(
            state="Karnataka",
            district="Bengaluru Rural",
            city="Nelamangala",
            pin_code="562123",
            area_type=AreaType.RURAL,
        ),
        financial=FinancialSection(
            annual_turnover_inr=8500000.0,  # 85 Lakhs
            investment_inr=3200000.0,      # 32 Lakhs
            employee_count=14,
            has_existing_loan=True,
            has_bank_finance=True,
            msme_classification=MSMEClassification.MICRO,
        ),
        characteristics=CharacteristicsSection(
            is_women_owned=True,
            social_category=SocialCategory.OBC,
            is_first_gen_entrepreneur=True,
            is_rural_enterprise=True,
            exports_currently=False,
            export_intent=True,
        ),
        registrations=[
            RegistrationEntry(type=RegistrationType.UDYAM, status=RegistrationStatus.REGISTERED),
            RegistrationEntry(type=RegistrationType.GST, status=RegistrationStatus.REGISTERED),
            RegistrationEntry(type=RegistrationType.PAN, status=RegistrationStatus.REGISTERED),
        ],
    )


@pytest.mark.asyncio
async def test_decision_intelligence_orchestration_comprehensive():
    service = DecisionIntelligenceService()
    profile = make_test_profile()

    request = DecisionRequest(objective=DecisionObjective.COMPREHENSIVE, top_k=5)
    response = await service.orchestrate(profile=profile, documents=[], request=request)

    # 1. Business Overview assertions
    assert response.business_overview["business_name"] == "Apex Precision Engineering"
    assert response.business_overview["msme_classification"] == "Micro"
    assert response.business_overview["is_women_owned"] is True
    assert response.business_overview["employee_count"] == 14

    # 2. Executive Decision Summary
    assert response.decision_summary["objective"] == "comprehensive"
    assert 50 <= response.decision_summary["executive_readiness_score"] <= 100
    assert "Apex Precision Engineering" in response.decision_summary["verdict_headline"]

    # 3. Multi-Agent Orchestration Status
    statuses = response.orchestration_status
    assert "profile_agent" in statuses
    assert "eligibility_agent" in statuses
    assert "rag_intelligence_agent" in statuses
    assert "recommendation_engine" in statuses
    assert "loan_advisory_agent" in statuses
    assert "compliance_agent" in statuses
    assert "permission_license_agent" in statuses
    assert "export_agent" in statuses

    assert statuses["profile_agent"].status in ("success", "partial")
    assert statuses["eligibility_agent"].status == "success"

    # 4. Top Scheme Recommendations & Explainability
    assert len(response.top_scheme_recommendations) >= 3
    top_scheme = response.top_scheme_recommendations[0]
    assert top_scheme.rank == 1
    assert top_scheme.btl_theta_score > 0
    assert top_scheme.win_probability > 0
    assert "Bradley-Terry-Luce" in top_scheme.why_recommended
    assert len(top_scheme.driving_profile_factors) > 0
    assert top_scheme.official_url.startswith("http")

    # 5. Pairwise Matrix & Features
    pairwise = response.pairwise_explainability
    assert len(pairwise.matrix) == len(response.top_scheme_recommendations)
    assert len(pairwise.matrix[0]) == len(response.top_scheme_recommendations)
    assert "business_sector_match" in pairwise.feature_importance
    assert len(pairwise.traceable_path) == 6

    # 6. Loan Advisory
    loan = response.loan_advisory
    assert loan.estimated_dscr > 0
    assert len(loan.recommended_options) >= 2
    assert "CGTMSE" in loan.recommended_options[0]["name"]

    # 7. Compliance & Permission Advisories
    assert response.compliance_advisory.rules_evaluated > 0
    assert response.permission_license_advisory.licenses_held >= 3
    assert response.permission_license_advisory.licenses_required >= 5

    # 8. Export Advisory
    assert response.export_advisory.readiness_score >= 0
    assert response.export_advisory.export_status in ("Active Exporter", "Export Ready / Interested", "Domestic Unit (Export Capable)")

    # 9. Prioritized Action Plan
    plan = response.prioritized_action_plan
    assert len(plan.phase1_immediate) >= 1
    assert len(plan.phase2_application) >= 1
    assert len(plan.phase3_expansion) >= 1


@pytest.mark.asyncio
async def test_decision_intelligence_loan_objective():
    service = DecisionIntelligenceService()
    profile = make_test_profile()

    request = DecisionRequest(
        objective=DecisionObjective.LOAN_FINANCE,
        target_loan_amount_inr=2500000.0,
        target_loan_purpose="Machinery Purchase & Expansion",
    )
    response = await service.orchestrate(profile=profile, documents=[], request=request)

    assert response.decision_summary["objective"] == "loan_finance"
    assert response.loan_advisory.funding_requirement == "₹25.00 Lakh"
    assert response.loan_advisory.loan_category == "Machinery Purchase & Expansion"


def test_permission_license_service_evaluation():
    perm_service = PermissionLicenseService()
    profile = make_test_profile()

    eval_result = perm_service.evaluate(profile)
    assert eval_result["licenses_held"] >= 3
    assert eval_result["licenses_required"] >= 6

    names = [lic["name"] for lic in eval_result["mandatory_licenses"]]
    assert any("Udyam" in n for n in names)
    assert any("GST" in n for n in names)
    assert any("Factory License" in n for n in names)  # 14 employees in manufacturing
    assert any("Pollution" in n for n in names)       # Fabrication & Machine Tools
