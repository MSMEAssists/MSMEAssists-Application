from app.models.document_model import DocumentModel
from app.models.profile_model import BusinessSection, CompletenessSnapshot, ProfileModel
from app.services import completeness_service
from app.utils.object_id import PyObjectId


def _bare_profile(**overrides) -> ProfileModel:
    defaults = dict(user_id=PyObjectId())
    defaults.update(overrides)
    return ProfileModel(**defaults)


def test_empty_profile_has_zero_percent_and_all_missing():
    profile = _bare_profile()
    completeness = completeness_service.compute_completeness(profile, documents=[])
    assert completeness.percentage == 0
    assert all(v is False for v in completeness.sections.values())


def test_business_only_profile_is_one_sixth_complete():
    profile = _bare_profile(
        business=BusinessSection(
            name="Meridian Fabrication Works",
            type="manufacturing",
            industry="Metal & Engineering Products",
            established_date="2019-06-12",
        ),
        completeness=CompletenessSnapshot(sections={"business": True}),
    )
    completeness = completeness_service.compute_completeness(profile, documents=[])
    assert completeness.sections["business"] is True
    # 1 of 6 sections => 17% (rounded)
    assert completeness.percentage == 17


def test_documents_section_true_only_with_non_rejected_document():
    profile = _bare_profile()
    rejected_doc = DocumentModel(
        user_id=profile.user_id,
        profile_id=profile.id,
        document_type="trade_license",
        file_name="license.png",
        mime_type="image/png",
        size_bytes=1000,
        storage_backend="local",
        storage_key="key",
        status="rejected",
    )
    sections_with_only_rejected = completeness_service.compute_sections(profile, [rejected_doc])
    assert sections_with_only_rejected["documents"] is False

    verified_doc = rejected_doc.model_copy(update={"status": "verified"})
    sections_with_verified = completeness_service.compute_sections(profile, [rejected_doc, verified_doc])
    assert sections_with_verified["documents"] is True


def test_missing_list_flags_not_registered_and_rejected_documents():
    from app.models.profile_model import RegistrationEntry

    profile = _bare_profile(
        business=BusinessSection(
            name="Meridian Fabrication Works",
            type="manufacturing",
            industry="Metal & Engineering Products",
            established_date="2019-06-12",
        ),
        registrations=[RegistrationEntry(type="trade_license", status="not_registered")],
        completeness=CompletenessSnapshot(sections={"business": True, "registrations": True}),
    )
    rejected_doc = DocumentModel(
        user_id=profile.user_id,
        profile_id=profile.id,
        document_type="trade_license",
        file_name="Trade_License_Old.png",
        mime_type="image/png",
        size_bytes=1000,
        storage_backend="local",
        storage_key="key",
        status="rejected",
    )

    _, missing = completeness_service.compute_completeness_with_missing(profile, [rejected_doc])
    details = [m.detail for m in missing]
    assert any("Trade License not registered" in d for d in details)
    assert any("Trade_License_Old.png rejected" in d for d in details)
