from app.core.constants import MSMEClassification
from app.models.profile_model import (
    BusinessSection,
    CharacteristicsSection,
    FinancialSection,
    ProfileModel,
    RegistrationEntry,
)
from app.services import eligibility_service
from app.utils.object_id import PyObjectId


def test_micro_classification_thresholds():
    financial = FinancialSection(annual_turnover_inr=4_00_00_000, investment_inr=90_00_000, employee_count=10)
    assert eligibility_service.compute_msme_classification(financial) == MSMEClassification.MICRO


def test_small_classification_thresholds():
    financial = FinancialSection(annual_turnover_inr=38_500_000, investment_inr=92_00_000 + 0, employee_count=34)
    # turnover 3.85cr, investment slightly above micro cap forces "small" only if investment > 1cr
    financial = FinancialSection(annual_turnover_inr=38_500_000, investment_inr=1_50_00_000, employee_count=34)
    assert eligibility_service.compute_msme_classification(financial) == MSMEClassification.SMALL


def test_medium_classification_thresholds():
    financial = FinancialSection(annual_turnover_inr=100_00_00_000, investment_inr=20_00_00_000, employee_count=200)
    assert eligibility_service.compute_msme_classification(financial) == MSMEClassification.MEDIUM


def test_beyond_medium_is_not_classified():
    financial = FinancialSection(annual_turnover_inr=500_00_00_000, investment_inr=100_00_00_000, employee_count=1000)
    assert eligibility_service.compute_msme_classification(financial) == MSMEClassification.NOT_CLASSIFIED


def test_none_financial_is_not_classified():
    assert eligibility_service.compute_msme_classification(None) == MSMEClassification.NOT_CLASSIFIED


def test_attributes_reflect_business_and_characteristics_and_registrations():
    profile = ProfileModel(
        user_id=PyObjectId(),
        business=BusinessSection(
            name="Meridian Fabrication Works",
            type="manufacturing",
            industry="Metal & Engineering Products",
            established_date="2019-06-12",
        ),
        characteristics=CharacteristicsSection(
            is_women_owned=False,
            is_first_gen_entrepreneur=True,
            export_intent=True,
            is_tech_oriented=True,
        ),
        registrations=[
            RegistrationEntry(type="udyam", status="registered"),
            RegistrationEntry(type="gst", status="registered"),
            RegistrationEntry(type="trade_license", status="not_registered"),
            RegistrationEntry(type="fssai", status="not_applicable"),
        ],
    )

    attributes = eligibility_service.compute_attributes(profile)

    assert "manufacturing_sector" in attributes
    assert "women_owned:false" in attributes
    assert "first_generation_entrepreneur" in attributes
    assert "export_intent" in attributes
    assert "technology_oriented" in attributes
    assert "udyam_registered" in attributes
    assert "gst_registered" in attributes
    assert "trade_license_missing" in attributes
    # not_applicable registrations carry no eligibility signal
    assert not any(a.startswith("fssai_") for a in attributes)
