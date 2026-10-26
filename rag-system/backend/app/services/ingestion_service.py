"""
Orchestrates Pipeline 1 (Knowledge Ingestion):

Official Government Website -> Source Validation -> URL Discovery ->
URL Validation -> Content Fetch -> HTML/PDF Detection -> Content
Extraction -> Cleaning -> Normalization -> Deduplication -> Document
Versioning -> Knowledge Classification -> Chunking -> Embedding ->
Vector Database
"""
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple

INGESTION_LOCK = threading.Lock()


def is_ingestion_running() -> bool:
    """Return True if any ingestion job (web, local, or discovered) is currently executing."""
    return INGESTION_LOCK.locked()

from app.chunking.chunker import chunk_document
from app.collectors.discovery import GovernmentDiscoveryService
from app.collectors.html_collector import collect_from_source
from app.core.config import settings
from app.core.source_registry import ApprovedSource
from app.db.repository import SQLiteRepository
from app.embeddings.embedding_service import EmbeddingService
from app.extractors.html_extractor import extract_html
from app.extractors.pdf_extractor import extract_pdf
from app.models.entities import (
    Chunk, ContentFormat, Document, DocumentVersion, KnowledgeItem,
    KnowledgeType, ProcessingJob, RawFetchResult, content_hash, new_id, now_ts,
)
from app.processors.classifier import classify, extract_fields
from app.processors.cleaner import clean_pdf_pages, clean_text
from app.processors.deduplicator import decide
from app.provenance.provenance import build_provenance_record
from app.vectorstore.base import VectorRecord, VectorStore

logger = logging.getLogger(__name__)

# Maps classifier field-extraction keys to KnowledgeItem attribute names
# where they differ (e.g. LOAN's "eligibility" section maps onto the
# eligible_applicants field).
_LOAN_FIELD_ALIAS = {"eligibility": "eligible_applicants"}


def _extracted_to_document_and_knowledge(
    extracted, raw: RawFetchResult, source: ApprovedSource, existing_document_id: Optional[str], version: int,
):
    doc_id = existing_document_id or new_id("doc")
    hash_ = content_hash(raw.raw_bytes)

    from app.core.local_documents import LOCAL_PDF_REGISTRY
    local_meta = next((v for v in LOCAL_PDF_REGISTRY.values() if v.official_url == raw.final_url), None)

    title = extracted.title
    if local_meta and local_meta.title:
        title = local_meta.title
    elif not title or title.lower().startswith("microsoft word") or title.lower().endswith(".cdr") or title.lower() in ("untitled", "none"):
        lines = [l.strip() for l in (extracted.text or "").split("\n") if l.strip()]
        title = lines[0][:120] if lines else (raw.final_url.split("/")[-1] or "Government Document")

    document = Document(
        document_id=doc_id,
        source_id=source.source_id,
        organization=source.organization,
        url=raw.final_url,
        content_format=raw.content_format,
        title=title,
        content_hash=hash_,
        version=version,
        retrieved_at=raw.fetched_at,
        publication_date=extracted.metadata.get("publication_date") or extracted.metadata.get("date"),
        last_updated_date=extracted.metadata.get("last_updated") or extracted.metadata.get("modified"),
    )

    knowledge_type = classify(title, extracted.text)
    document.knowledge_type = knowledge_type

    knowledge_item = None
    if knowledge_type in (KnowledgeType.SCHEME, KnowledgeType.LOAN):
        raw_fields = extract_fields(knowledge_type, title, extracted.text, extracted.headings)
        if knowledge_type == KnowledgeType.LOAN:
            raw_fields = {_LOAN_FIELD_ALIAS.get(k, k): v for k, v in raw_fields.items()}

        from app.core.url_validator import verify_direct_application_url
        candidate_app_url = None
        if local_meta and getattr(local_meta, "official_application_url", None):
            candidate_app_url = local_meta.official_application_url
        elif extracted.metadata.get("official_application_url"):
            candidate_app_url = extracted.metadata.get("official_application_url")

        verified_app_url = verify_direct_application_url(candidate_app_url, [source])

        knowledge_item = KnowledgeItem(
            knowledge_id=new_id("know"),
            document_id=doc_id,
            source_id=source.source_id,
            knowledge_type=knowledge_type,
            title=title,
            original_source_url=raw.final_url,
            source_organization=source.organization,
            official_application_url=verified_app_url,
            publication_date=document.publication_date,
            last_updated_date=document.last_updated_date,
            **raw_fields,
        )

    return document, knowledge_item


class IngestionService:
    def __init__(
        self,
        repository: SQLiteRepository,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        approved_sources: List[ApprovedSource],
        discovery_service: Optional[GovernmentDiscoveryService] = None,
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.approved_sources = approved_sources
        self.discovery_service = discovery_service or GovernmentDiscoveryService(repository=self.repository)

    def _refresh_approved_sources_from_repo(self):
        """Sync in-memory approved sources with newly discovered or admin-added sources in repository."""
        if self.repository and hasattr(self.repository, "list_sources"):
            stored = self.repository.list_sources()
            known_ids = {s.source_id for s in self.approved_sources}
            for r in stored:
                if isinstance(r, dict) and r.get("source_id") not in known_ids and "allowed_domains" in r:
                    self.approved_sources.append(ApprovedSource(**r))

    def _find_matching_source(self, url: str) -> Optional[ApprovedSource]:
        """Resolve which ApprovedSource owns a URL by checking allowed_domains."""
        from urllib.parse import urlparse
        hostname = (urlparse(url).hostname or "").lower()
        if not hostname:
            return None
        for s in self.approved_sources:
            for d in s.allowed_domains:
                clean_d = d.lower().rstrip(".")
                if hostname == clean_d or hostname.endswith("." + clean_d):
                    return s
        return None

    def run_ingestion(
        self,
        source_id: Optional[str] = None,
        max_pages: Optional[int] = None,
        resolve_dns: bool = True,
        enable_discovery: bool = True,
    ) -> ProcessingJob:
        acquired = INGESTION_LOCK.acquire(blocking=False)
        if not acquired:
            job = ProcessingJob(
                job_id=new_id("job"),
                source_id=source_id,
                status="failed",
                started_at=now_ts(),
                finished_at=now_ts(),
                errors=["An ingestion job is already running in this process."],
            )
            self.repository.upsert_job(job)
            return job

        job = ProcessingJob(job_id=new_id("job"), source_id=source_id, status="running", started_at=now_ts())
        self.repository.upsert_job(job)

        self._refresh_approved_sources_from_repo()
        targets = [s for s in self.approved_sources if s.enabled and (source_id is None or s.source_id == source_id)]

        try:
            per_source_raw: Dict[str, List[RawFetchResult]] = {}
            all_texts_for_fit: List[str] = []

            sources_queue: List[ApprovedSource] = list(targets)
            processed_source_ids: Set[str] = set()
            max_discovered_sources = getattr(settings, "discovery_max_sources_per_run", 10)
            discovered_crawled_count = 0

            # Pass 1: Crawl sources with graceful per-source failure isolation
            while sources_queue:
                source = sources_queue.pop(0)
                if source.source_id in processed_source_ids:
                    continue
                processed_source_ids.add(source.source_id)

                try:
                    raw_results = collect_from_source(
                        source,
                        self.approved_sources,
                        max_pages=max_pages,
                        resolve_dns=resolve_dns,
                        discovery_service=self.discovery_service,
                        enable_discovery=enable_discovery,
                    )
                    job.documents_discovered += len(raw_results)
                    per_source_raw[source.source_id] = raw_results
                    for raw in raw_results:
                        try:
                            text = self._extract_and_clean_text_only(raw)
                            if text:
                                all_texts_for_fit.append(text)
                        except Exception:
                            continue
                except Exception as e:
                    # Individual source failure does not halt the entire ingestion run
                    job.errors.append(f"Source '{source.source_id}' crawl failed: {e}")
                    logger.exception("Failed to collect from source %s", source.source_id)

                # Dynamically queue newly discovered sources to crawl their content too
                if enable_discovery and source_id is None and discovered_crawled_count < max_discovered_sources:
                    self._refresh_approved_sources_from_repo()
                    for s in self.approved_sources:
                        if s.enabled and s.source_id not in processed_source_ids and s not in sources_queue:
                            sources_queue.append(s)
                            discovered_crawled_count += 1
                            if discovered_crawled_count >= max_discovered_sources:
                                break

            # Pass 2: Calibrate/fit embeddings over full corpus (newly discovered + existing)
            existing_chunk_texts = [c["text"] for c in self.repository._list("chunks")] if hasattr(self.repository, "_list") else []
            self.embedding_service.fit(all_texts_for_fit + existing_chunk_texts)

            # Pass 3: Ingest, chunk, embed, index, and build provenance
            for s_id, raws in per_source_raw.items():
                fallback_source = next((s for s in self.approved_sources if s.source_id == s_id), None)
                for raw in raws:
                    try:
                        actual_source = self._find_matching_source(raw.final_url) or fallback_source
                        if not actual_source:
                            from app.core.source_registry import create_discovered_source
                            actual_source = create_discovered_source(raw.final_url)
                        outcome = self._ingest_one(raw, actual_source)
                        if outcome == "ingested":
                            job.documents_ingested += 1
                        elif outcome == "unchanged":
                            job.documents_unchanged += 1
                    except Exception as e:
                        job.errors.append(f"{raw.url}: {e}")
                        logger.exception("Failed to ingest %s", raw.url)

            self.vector_store.persist()
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))
            logger.exception("Ingestion job failed")
        finally:
            job.finished_at = now_ts()
            self.repository.upsert_job(job)
            INGESTION_LOCK.release()

        return job

    def ingest_local_documents(
        self,
        documents_dir: Optional[str] = None,
        source_id: Optional[str] = None,
        custom_registry: Optional[dict] = None,
    ) -> ProcessingJob:
        """Ingests approved local PDF documents from data/source_documents/
        by looking up their verified canonical official URLs and sources,
        running them through the exact same extraction, cleaning, chunking,
        embedding, and provenance pipeline as remote URLs."""
        import os
        from app.core.config import settings
        from app.core.local_documents import LOCAL_PDF_REGISTRY, get_local_document_metadata
        from app.core.url_validator import validate_url

        acquired = INGESTION_LOCK.acquire(blocking=False)
        if not acquired:
            job = ProcessingJob(
                job_id=new_id("job"),
                source_id=source_id,
                status="failed",
                started_at=now_ts(),
                finished_at=now_ts(),
                errors=["An ingestion job is already running in this process."],
            )
            self.repository.upsert_job(job)
            return job

        job = ProcessingJob(job_id=new_id("job"), source_id=source_id, status="running", started_at=now_ts())
        self.repository.upsert_job(job)

        try:
            dir_path = documents_dir or settings.source_documents_path
            if not os.path.exists(dir_path):
                job.status = "failed"
                job.errors.append(f"Directory not found: {dir_path}")
                return job

            registry = custom_registry or LOCAL_PDF_REGISTRY
            sources_by_id = {s.source_id: s for s in self.approved_sources}

            files_to_process = []
            for fname in sorted(os.listdir(dir_path)):
                if not fname.lower().endswith(".pdf"):
                    continue
                meta = registry.get(fname) or get_local_document_metadata(fname)
                if not meta:
                    logger.warning("Skipping unregistered local PDF: %s", fname)
                    continue
                if source_id and meta.source_id != source_id:
                    continue
                files_to_process.append((fname, meta))

            job.documents_discovered = len(files_to_process)

            all_raw_items = []
            all_texts_for_fit: List[str] = []

            for fname, meta in files_to_process:
                fpath = os.path.join(dir_path, fname)
                try:
                    with open(fpath, "rb") as f:
                        file_bytes = f.read()
                except Exception as e:
                    job.errors.append(f"Could not read {fname}: {e}")
                    continue

                # Validate canonical official URL against approved sources
                val = validate_url(meta.official_url, self.approved_sources, resolve_dns=False)
                if not val.is_valid:
                    job.errors.append(f"Invalid URL for {fname}: {val.reason}")
                    continue

                matched_source = sources_by_id.get(meta.source_id) or val.matched_source
                if not matched_source:
                    job.errors.append(f"Source {meta.source_id} not found in approved sources")
                    continue

                raw = RawFetchResult(
                    url=meta.official_url,
                    final_url=meta.official_url,
                    status_code=200,
                    content_format=ContentFormat.PDF,
                    raw_bytes=file_bytes,
                    fetched_at=now_ts(),
                )
                all_raw_items.append((raw, matched_source))
                try:
                    text = self._extract_and_clean_text_only(raw)
                    if text:
                        all_texts_for_fit.append(text)
                except Exception as e:
                    logger.warning("Failed text extraction for %s: %s", fname, e)

            # Fit embedding service on corpus + existing chunk texts
            existing_chunk_texts = [c["text"] for c in self.repository._list("chunks")] if hasattr(self.repository, "_list") else []
            self.embedding_service.fit(all_texts_for_fit + existing_chunk_texts)

            for raw, source in all_raw_items:
                try:
                    outcome = self._ingest_one(raw, source)
                    if outcome == "ingested":
                        job.documents_ingested += 1
                    elif outcome == "unchanged":
                        job.documents_unchanged += 1
                except Exception as e:
                    job.errors.append(f"{raw.url}: {e}")
                    logger.exception("Failed to ingest %s", raw.url)

            self.vector_store.persist()
            job.status = "completed"
        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))
            logger.exception("Local ingestion job failed")
        finally:
            job.finished_at = now_ts()
            self.repository.upsert_job(job)
            INGESTION_LOCK.release()

        return job

    def discover_sources(
        self,
        seed_urls: Optional[List[str]] = None,
        max_sources: int = 10,
        max_urls_per_source: int = 50,
        resolve_dns: bool = True,
        ingest_discovered: bool = True,
    ) -> Dict[str, Any]:
        """Discover new official government portals and scheme pages, register them in repository,
        and ingest their content through the chunking, embedding, and vector indexing pipeline."""
        seeds = seed_urls or [s.base_url for s in self.approved_sources if s.enabled]
        discovered_urls_map: Dict[str, Any] = {}
        errors: List[str] = []

        initial_sources_count = len(self.repository.list_sources()) if self.repository and hasattr(self.repository, "list_sources") else len(self.approved_sources)

        for seed in seeds[:max_sources]:
            try:
                urls = self.discovery_service.discover_from_sitemaps(
                    seed, resolve_dns=resolve_dns, max_urls=max_urls_per_source
                )
                for item in urls:
                    discovered_urls_map[item.normalized_url] = item
            except Exception as e:
                errors.append(f"Discovery error for {seed}: {e}")

        self._refresh_approved_sources_from_repo()

        documents_ingested = 0
        documents_unchanged = 0

        # Ingest discovered pages through extraction, chunking, embedding, vector store, and provenance
        if ingest_discovered and discovered_urls_map:
            acquired = INGESTION_LOCK.acquire(blocking=False)
            if not acquired:
                errors.append("An ingestion job is already running; skipping immediate indexing of discovered pages.")
            else:
                try:
                    from app.utils.http import fetch
                    raw_items: List[Tuple[RawFetchResult, ApprovedSource]] = []
                    all_texts_for_fit: List[str] = []

                    for norm_url, disc_item in discovered_urls_map.items():
                        try:
                            source = self._find_matching_source(norm_url)
                            if not source:
                                source = self.discovery_service.register_or_get_source(norm_url)
                                if source:
                                    self._refresh_approved_sources_from_repo()

                            if not source:
                                continue

                            if not self.discovery_service.robots_manager.can_fetch(norm_url):
                                continue
                            self.discovery_service.rate_limiter.acquire(disc_item.hostname)

                            raw = fetch(norm_url)
                            raw_items.append((raw, source))
                            text = self._extract_and_clean_text_only(raw)
                            if text:
                                all_texts_for_fit.append(text)
                        except Exception as e:
                            errors.append(f"Fetch failed for {norm_url}: {e}")

                    if all_texts_for_fit:
                        existing_chunk_texts = [c["text"] for c in self.repository._list("chunks")] if hasattr(self.repository, "_list") else []
                        self.embedding_service.fit(all_texts_for_fit + existing_chunk_texts)

                    for raw, source in raw_items:
                        try:
                            outcome = self._ingest_one(raw, source)
                            if outcome == "ingested":
                                documents_ingested += 1
                            elif outcome == "unchanged":
                                documents_unchanged += 1
                        except Exception as e:
                            errors.append(f"{raw.url}: {e}")
                            logger.exception("Failed to ingest discovered page %s", raw.url)

                    if documents_ingested > 0:
                        self.vector_store.persist()
                finally:
                    INGESTION_LOCK.release()

        total_sources = len(self.repository.list_sources()) if self.repository and hasattr(self.repository, "list_sources") else len(self.approved_sources)

        return {
            "status": "completed",
            "sources_registered_total": total_sources,
            "new_sources_discovered": max(0, total_sources - initial_sources_count),
            "urls_discovered": len(discovered_urls_map),
            "documents_ingested": documents_ingested,
            "documents_unchanged": documents_unchanged,
            "errors": errors,
        }


    def _extract_and_clean_text_only(self, raw: RawFetchResult) -> str:
        """Cheap first-pass extraction used only to build the fitting
        corpus for the embedding service -- does not touch the DB."""
        if raw.content_format == ContentFormat.HTML:
            extracted = extract_html(raw.raw_bytes.decode("utf-8", errors="ignore"), raw.final_url)
            return clean_text(extracted.text)
        extracted = extract_pdf(raw.raw_bytes)
        return clean_text("\n".join(extracted.page_texts or []))

    def _ingest_one(self, raw: RawFetchResult, source: ApprovedSource) -> str:
        existing = self.repository.find_document_by_url(raw.final_url)
        dedup = decide(
            raw.raw_bytes,
            existing["document_id"] if existing else None,
            existing["content_hash"] if existing else None,
        )
        if dedup.is_unchanged:
            return "unchanged"

        version = 1 if dedup.is_new else (existing["version"] + 1)

        if raw.content_format == ContentFormat.HTML:
            extracted = extract_html(raw.raw_bytes.decode("utf-8", errors="ignore"), raw.final_url)
            extracted.text = clean_text(extracted.text)
        else:
            extracted = extract_pdf(raw.raw_bytes)
            extracted.page_texts = clean_pdf_pages(extracted.page_texts or [])
            extracted.text = clean_text("\n".join(extracted.page_texts))

        document, knowledge_item = _extracted_to_document_and_knowledge(
            extracted, raw, source, dedup.existing_document_id, version
        )

        self.repository.upsert_document(document)
        self.repository.add_document_version(
            DocumentVersion(
                document_id=document.document_id,
                version=version,
                content_hash=document.content_hash,
                retrieved_date=raw.fetched_at,
                publication_date=document.publication_date,
                last_updated_date=document.last_updated_date,
            )
        )

        self.repository.delete_knowledge_items_for_document(document.document_id)
        if knowledge_item:
            self.repository.upsert_knowledge_item(knowledge_item)

        old_chunk_ids = self.repository.delete_chunks_for_document(document.document_id)
        if old_chunk_ids:
            self.vector_store.delete(old_chunk_ids)

        spans = chunk_document(extracted.text, page_texts=extracted.page_texts)
        chunks: List[Chunk] = []
        for idx, span in enumerate(spans):
            chunks.append(
                Chunk(
                    chunk_id=new_id("chunk"),
                    document_id=document.document_id,
                    source_id=source.source_id,
                    knowledge_id=knowledge_item.knowledge_id if knowledge_item else None,
                    knowledge_type=document.knowledge_type,
                    title=document.title,
                    section=span.section,
                    page_number=span.page_number,
                    chunk_index=idx,
                    text=span.text,
                )
            )

        if chunks:
            self.repository.upsert_chunks(chunks)

            embedding_result = self.embedding_service.embed([c.text for c in chunks])
            vector_records = [
                VectorRecord(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    source_id=c.source_id,
                    knowledge_type=c.knowledge_type.value,
                    vector=vec,
                )
                for c, vec in zip(chunks, embedding_result.vectors)
            ]
            self.vector_store.upsert(vector_records)

            for c in chunks:
                record = build_provenance_record(c, document, knowledge_item, source)
                self.repository.upsert_provenance(record)

        return "ingested" if dedup.is_new else "ingested"
