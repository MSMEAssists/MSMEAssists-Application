"""
Provenance: builds and resolves the mandatory chain

    Answer -> Retrieved Chunk -> Document -> Knowledge Item ->
    Approved Government Source -> Official URL

Every retrieval result must be traceable back to an official government
URL. This module is the only place that constructs ProvenanceRecord
objects, so the chain can't be produced inconsistently across the codebase.
"""
from typing import Optional

from app.models.entities import Chunk, Document, KnowledgeItem, ProvenanceRecord
from app.core.source_registry import ApprovedSource


def build_provenance_record(
    chunk: Chunk,
    document: Document,
    knowledge_item: Optional[KnowledgeItem],
    source: ApprovedSource,
) -> ProvenanceRecord:
    return ProvenanceRecord(
        chunk_id=chunk.chunk_id,
        document_id=document.document_id,
        knowledge_id=knowledge_item.knowledge_id if knowledge_item else None,
        source_id=source.source_id,
        source_name=source.name,
        organization=source.organization,
        official_url=document.url,
        page_number=chunk.page_number,
        publication_date=document.publication_date,
        last_updated_date=document.last_updated_date,
    )
