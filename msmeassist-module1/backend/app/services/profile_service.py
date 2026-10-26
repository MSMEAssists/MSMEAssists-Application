"""
Profile service.

Owns:
  - creating/updating the business_profiles document, section by section
  - deriving financial.msme_classification server-side (never client-writable)
  - normalizing the stored Mongo document into the public ProfileResponse
    shape documented in docs/module-1-api.md / docs/module-2-integration.md
  - masking registration identifiers before they ever leave this layer
  - writing an audit log entry for every create/update
"""
from datetime import date, datetime, time, timezone
from typing import List, Optional

from app.core.constants import AuditAction, ProfileStatus
from app.models.audit_log_model import ProfileAuditLogModel
from app.models.document_model import DocumentModel
from app.models.profile_model import (
    BusinessSection,
    CharacteristicsSection,
    FinancialSection,
    LocationSection,
    ProfileModel,
    RegistrationEntry,
)
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile_schema import (
    BusinessSectionOut,
    CharacteristicsSectionOut,
    CompletenessOut,
    FinancialSectionOut,
    LocationSectionOut,
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RegistrationOut,
)
from app.services import completeness_service, eligibility_service
from app.utils.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.utils.formatters import mask_identifier


class ProfileService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        document_repo: DocumentRepository,
        audit_repo: AuditLogRepository,
    ):
        self.profile_repo = profile_repo
        self.document_repo = document_repo
        self.audit_repo = audit_repo

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def get_profile(self, user_id) -> ProfileResponse:
        profile = await self.profile_repo.find_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError("No business profile found for this user")
        documents = await self.document_repo.find_by_profile_id(profile.id)
        return self._to_response(profile, documents)

    async def get_profile_model(self, user_id) -> Optional[ProfileModel]:
        return await self.profile_repo.find_by_user_id(user_id)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create_profile(self, user_id, payload: ProfileCreateRequest) -> ProfileResponse:
        existing = await self.profile_repo.find_by_user_id(user_id)
        if existing is not None:
            raise ProfileAlreadyExistsError("A profile already exists for this user — use PUT to update it")

        profile = ProfileModel(user_id=user_id)
        touched: dict[str, bool] = {}

        profile.business = self._build_business_section(payload.business)
        touched["business"] = True

        if payload.location is not None:
            profile.location = LocationSection(**payload.location.model_dump())
            touched["location"] = True

        if payload.financial is not None:
            profile.financial = self._build_financial_section(payload.financial)
            touched["financial"] = True

        if payload.characteristics is not None:
            profile.characteristics = CharacteristicsSection(**payload.characteristics.model_dump())
            touched["characteristics"] = True

        if payload.registrations is not None:
            profile.registrations = [RegistrationEntry(**r.model_dump()) for r in payload.registrations]
            touched["registrations"] = True

        profile.completeness.sections = touched
        profile.status = ProfileStatus.DRAFT

        profile = await self.profile_repo.insert(profile)
        await self._recompute_and_persist_completeness(profile)
        await self._write_audit_log(user_id, profile.id, AuditAction.CREATED, list(touched.keys()))

        documents = await self.document_repo.find_by_profile_id(profile.id)
        return self._to_response(profile, documents)

    async def update_profile(self, user_id, payload: ProfileUpdateRequest) -> ProfileResponse:
        profile = await self.profile_repo.find_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError("No business profile found for this user — create one first")

        touched_sections: dict[str, bool] = dict(profile.completeness.sections)
        changed_fields: List[str] = []
        update_doc: dict = {}

        if payload.business is not None:
            profile.business = self._build_business_section(payload.business)
            update_doc["business"] = profile.business.model_dump()
            touched_sections["business"] = True
            changed_fields.append("business")

        if payload.location is not None:
            profile.location = LocationSection(**payload.location.model_dump())
            update_doc["location"] = profile.location.model_dump()
            touched_sections["location"] = True
            changed_fields.append("location")

        if payload.financial is not None:
            profile.financial = self._build_financial_section(payload.financial)
            update_doc["financial"] = profile.financial.model_dump()
            touched_sections["financial"] = True
            changed_fields.append("financial")

        if payload.characteristics is not None:
            profile.characteristics = CharacteristicsSection(**payload.characteristics.model_dump())
            update_doc["characteristics"] = profile.characteristics.model_dump()
            touched_sections["characteristics"] = True
            changed_fields.append("characteristics")

        if payload.registrations is not None:
            profile.registrations = [RegistrationEntry(**r.model_dump()) for r in payload.registrations]
            update_doc["registrations"] = [r.model_dump() for r in profile.registrations]
            touched_sections["registrations"] = True
            changed_fields.append("registrations")

        profile.completeness.sections = touched_sections
        update_doc["updated_at"] = datetime.now(timezone.utc)

        if update_doc:
            # NOTE: intentionally NOT reassigning `profile` from this call's
            # return value. `profile` already carries the correct in-memory
            # state (including the just-updated completeness.sections touch
            # flags) — reloading from the DB here would discard them, since
            # `update_doc` doesn't include the `completeness` key itself.
            await self.profile_repo.update_by_id(profile.id, update_doc)

        await self._recompute_and_persist_completeness(profile)
        if changed_fields:
            await self._write_audit_log(user_id, profile.id, AuditAction.UPDATED, changed_fields)

        documents = await self.document_repo.find_by_profile_id(profile.id)
        return self._to_response(profile, documents)

    async def recompute_completeness_for_profile_id(self, profile_id) -> None:
        """Called by document_service after upload/delete — documents affect completeness."""
        profile = await self.profile_repo.find_by_id(profile_id)
        if profile is None:
            return
        await self._recompute_and_persist_completeness(profile)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_business_section(business_in) -> BusinessSection:
        data = business_in.model_dump()
        established = data.pop("established_date")
        if isinstance(established, date) and not isinstance(established, datetime):
            established = datetime.combine(established, time.min)
        return BusinessSection(established_date=established, **data)

    @staticmethod
    def _build_financial_section(financial_in) -> FinancialSection:
        classification = eligibility_service.compute_msme_classification(
            FinancialSection(
                annual_turnover_inr=financial_in.annual_turnover_inr,
                investment_inr=financial_in.investment_inr,
                employee_count=financial_in.employee_count,
            )
        )
        return FinancialSection(
            **financial_in.model_dump(),
            msme_classification=classification,
        )

    async def _recompute_and_persist_completeness(self, profile: ProfileModel) -> ProfileModel:
        documents = await self.document_repo.find_by_profile_id(profile.id)
        completeness = completeness_service.compute_completeness(profile, documents)
        profile.completeness.percentage = completeness.percentage
        profile.completeness.sections = completeness.sections
        await self.profile_repo.update_by_id(
            profile.id,
            {
                "completeness": profile.completeness.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            },
        )
        return profile

    async def _write_audit_log(self, user_id, profile_id, action: AuditAction, changed_fields: List[str]) -> None:
        entry = ProfileAuditLogModel(
            user_id=user_id,
            profile_id=profile_id,
            action=action,
            changed_fields=changed_fields,
            actor="self",
        )
        await self.audit_repo.insert(entry)

    @staticmethod
    def _build_business_out(business: BusinessSection) -> BusinessSectionOut:
        data = business.model_dump()
        data["established_date"] = business.established_date.date()
        return BusinessSectionOut(**data)

    @staticmethod
    def _to_response(profile: ProfileModel, documents: List[DocumentModel]) -> ProfileResponse:
        registrations_out = [
            RegistrationOut(
                type=r.type,
                status=r.status,
                masked_identifier=mask_identifier(r.identifier) if r.identifier else None,
            )
            for r in profile.registrations
        ]

        completeness, _missing = completeness_service.compute_completeness_with_missing(profile, documents)

        return ProfileResponse(
            profile_id=str(profile.id),
            status=profile.status,
            business=ProfileService._build_business_out(profile.business) if profile.business else None,
            location=LocationSectionOut(**profile.location.model_dump()) if profile.location else None,
            financial=FinancialSectionOut(**profile.financial.model_dump()) if profile.financial else None,
            characteristics=(
                CharacteristicsSectionOut(**profile.characteristics.model_dump())
                if profile.characteristics
                else None
            ),
            registrations=registrations_out,
            completeness=CompletenessOut(percentage=completeness.percentage, sections=completeness.sections),
            updated_at=profile.updated_at,
        )
