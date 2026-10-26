"""
Completeness engine.

Computes the per-section boolean breakdown, overall percentage, and a
human-readable "missing" list. This is deliberately kept separate from
profile_service so its weighting rules can evolve independently (see
docs/architecture.md §1 — "Key architectural decisions").

Section-touched semantics:
  A section is marked complete the first time its data is submitted via
  POST/PUT, and stays complete thereafter (we don't punish a user for a
  field being technically "empty" once they've engaged with a step) —
  except `documents`, which is derived live from actual uploaded/verified
  document records, and `registrations`, whose per-item status can still
  surface follow-up items in `missing` even once the section is "touched".
"""
from typing import List

from app.core.constants import PROFILE_SECTIONS, DocumentStatus, RegistrationStatus
from app.models.document_model import DocumentModel
from app.models.profile_model import ProfileModel
from app.schemas.profile_schema import CompletenessOut, MissingItem

_SECTION_MISSING_MESSAGES = {
    "business": "Business details not provided",
    "location": "Location details not provided",
    "financial": "Financial details not provided",
    "characteristics": "Business characteristics not provided",
    "registrations": "Government registration details not provided",
    "documents": "No supporting documents uploaded",
}


def compute_sections(profile: ProfileModel, documents: List[DocumentModel]) -> dict[str, bool]:
    touched = dict(profile.completeness.sections) if profile.completeness else {}

    sections = {
        "business": bool(touched.get("business")) or profile.business is not None,
        "location": bool(touched.get("location")) or profile.location is not None,
        "financial": bool(touched.get("financial")) or profile.financial is not None,
        "characteristics": bool(touched.get("characteristics")),
        "registrations": bool(touched.get("registrations")) or len(profile.registrations) > 0,
        "documents": any(
            doc.status in (DocumentStatus.UPLOADED, DocumentStatus.PENDING_REVIEW, DocumentStatus.VERIFIED)
            for doc in documents
        ),
    }
    return sections


def compute_percentage(sections: dict[str, bool]) -> int:
    if not PROFILE_SECTIONS:
        return 0
    completed = sum(1 for s in PROFILE_SECTIONS if sections.get(s))
    return round((completed / len(PROFILE_SECTIONS)) * 100)


def compute_missing(sections: dict[str, bool], profile: ProfileModel, documents: List[DocumentModel]) -> List[MissingItem]:
    missing: List[MissingItem] = []

    for section, is_complete in sections.items():
        if not is_complete:
            missing.append(MissingItem(section=section, detail=_SECTION_MISSING_MESSAGES[section]))

    # Registration-level follow-ups even when the section itself is "touched"
    if sections.get("registrations"):
        for reg in profile.registrations:
            if reg.status == RegistrationStatus.NOT_REGISTERED:
                missing.append(
                    MissingItem(section="registrations", detail=f"{reg.type.value.replace('_', ' ').title()} not registered")
                )

    # Document-level follow-ups (rejected files need re-upload)
    for doc in documents:
        if doc.status == DocumentStatus.REJECTED:
            missing.append(
                MissingItem(section="documents", detail=f"{doc.file_name} rejected — re-upload required")
            )

    return missing


def compute_completeness(profile: ProfileModel, documents: List[DocumentModel]) -> CompletenessOut:
    sections = compute_sections(profile, documents)
    percentage = compute_percentage(sections)
    return CompletenessOut(percentage=percentage, sections=sections)


def compute_completeness_with_missing(
    profile: ProfileModel, documents: List[DocumentModel]
) -> tuple[CompletenessOut, List[MissingItem]]:
    sections = compute_sections(profile, documents)
    percentage = compute_percentage(sections)
    missing = compute_missing(sections, profile, documents)
    return CompletenessOut(percentage=percentage, sections=sections), missing
