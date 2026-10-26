"""
Deduplication: decide whether a freshly fetched page/PDF is new, unchanged,
or a new version of an existing document, using canonical URL + content hash.
"""
from dataclasses import dataclass
from typing import Optional

from app.models.entities import content_hash


@dataclass
class DedupDecision:
    is_new: bool
    is_unchanged: bool
    existing_document_id: Optional[str] = None
    new_content_hash: str = ""


def decide(
    raw_bytes: bytes,
    existing_document_id: Optional[str],
    existing_content_hash: Optional[str],
) -> DedupDecision:
    new_hash = content_hash(raw_bytes)

    if existing_document_id is None:
        return DedupDecision(is_new=True, is_unchanged=False, new_content_hash=new_hash)

    if existing_content_hash == new_hash:
        return DedupDecision(
            is_new=False,
            is_unchanged=True,
            existing_document_id=existing_document_id,
            new_content_hash=new_hash,
        )

    # Same canonical URL/document, but content differs -> new version, not a
    # brand-new document.
    return DedupDecision(
        is_new=False,
        is_unchanged=False,
        existing_document_id=existing_document_id,
        new_content_hash=new_hash,
    )
