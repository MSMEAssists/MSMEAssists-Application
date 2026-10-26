"""
Schemes Service.

Orchestrates business profile eligibility information with official government
intelligence retrieved from the RAG service.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.models.profile_model import ProfileModel
from app.schemas.schemes_schema import (
    DiscoveredSchemeOut,
    EligibilityStatus,
    SchemeCitationOut,
    SchemeDiscoveryResponse,
    SchemeQueryRequest,
    SchemeQueryResponse,
)
from app.services import eligibility_service
from app.services.advisor_service import AdvisorService
from app.services.rag_client import RagClient
from app.services.scheme_evaluator import SchemeEvaluator
from app.services.scheme_query_builder import SchemeQueryBuilder

logger = logging.getLogger(__name__)

# TTL Cache for discovered schemes: cache_key -> (timestamp, SchemeDiscoveryResponse)
_DISCOVERY_CACHE: Dict[str, Tuple[float, SchemeDiscoveryResponse]] = {}
# TTL Cache for chat assistant queries: cache_key -> (timestamp, SchemeQueryResponse)
_CHAT_CACHE: Dict[str, Tuple[float, SchemeQueryResponse]] = {}
_CACHE_TTL = 300.0  # 5 minutes


class SchemesService:
    def __init__(
        self,
        rag_client: Optional[RagClient] = None,
        query_builder: Optional[SchemeQueryBuilder] = None,
        evaluator: Optional[SchemeEvaluator] = None,
    ):
        self.rag_client = rag_client or RagClient()
        self.query_builder = query_builder or SchemeQueryBuilder()
        self.evaluator = evaluator or SchemeEvaluator()

    async def discover_schemes_for_profile(self, profile: Optional[ProfileModel]) -> SchemeDiscoveryResponse:
        # Check cache
        cache_key = "anonymous"
        if profile and profile.id:
            profile_ts = getattr(profile, "updated_at", None) or getattr(profile, "created_at", None) or ""
            cache_key = f"{profile.id}_{profile_ts}"
        elif profile and profile.business:
            cache_key = f"{profile.business.name}_{profile.business.type}_{profile.financial.annual_turnover_inr if profile.financial else ''}"

        now = time.time()
        if cache_key in _DISCOVERY_CACHE:
            ts, cached_resp = _DISCOVERY_CACHE[cache_key]
            if now - ts < _CACHE_TTL:
                logger.info("Serving discovered schemes from in-memory cache for key: %s", cache_key)
                return cached_resp

        business_name = profile.business.name if (profile and profile.business) else "Your Business"
        eligibility = eligibility_service.compute_eligibility(profile) if profile else None

        msme_class = eligibility.msme_classification.value if eligibility else "not_classified"
        attributes = eligibility.attributes if eligibility else []

        # 1. Build multi-perspective search queries
        search_queries = self.query_builder.build_queries(profile)

        # 2. Retrieve candidate chunks across queries concurrently and group by document
        doc_chunks_map: Dict[str, List[Dict[str, Any]]] = {}
        doc_meta_map: Dict[str, Dict[str, Any]] = {}

        # Run all queries in parallel via asyncio.gather
        search_tasks = [
            self.rag_client.search(query=q, top_k=6, similarity_threshold=0.0)
            for q in search_queries
        ]
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for query_results in all_results:
            if isinstance(query_results, Exception):
                logger.warning("Sub-query search encountered error: %s", query_results)
                continue
            for r in query_results:
                doc_key = r.get("official_url") or r.get("document_id") or r.get("chunk_id")
                if not doc_key:
                    continue
                if doc_key not in doc_chunks_map:
                    doc_chunks_map[doc_key] = []
                    doc_meta_map[doc_key] = {
                        "title": r.get("title") or "Government Program",
                        "organization": r.get("source_organization", "Government of India"),
                        "official_url": r.get("official_url", ""),
                        "official_application_url": r.get("official_application_url"),
                        "knowledge_type": r.get("knowledge_type", "SCHEME"),
                        "document_id": r.get("document_id"),
                        "chunk_id": r.get("chunk_id"),
                        "page_number": r.get("page_number"),
                    }
                doc_chunks_map[doc_key].append(r)

        # 3. Evaluate each document cluster against profile evidence
        discovered: List[DiscoveredSchemeOut] = []

        status_priority = {
            EligibilityStatus.ELIGIBLE: 4,
            EligibilityStatus.CONDITIONALLY_ELIGIBLE: 3,
            EligibilityStatus.POTENTIALLY_ELIGIBLE: 2,
            EligibilityStatus.INSUFFICIENT_EVIDENCE: 1,
            EligibilityStatus.NOT_ELIGIBLE: 0,
        }

        for doc_key, chunks in doc_chunks_map.items():
            meta = doc_meta_map[doc_key]
            eval_result = self.evaluator.evaluate_scheme(profile, chunks, meta)

            primary_chunk = chunks[0] if chunks else {}
            snippet_text = primary_chunk.get("text", "")
            snippet = snippet_text[:320] + ("..." if len(snippet_text) > 320 else "")

            discovered.append(
                DiscoveredSchemeOut(
                    id=primary_chunk.get("chunk_id", doc_key),
                    title=meta["title"],
                    knowledge_type=meta["knowledge_type"],
                    organization=meta["organization"],
                    official_url=meta["official_url"],
                    official_application_url=meta.get("official_application_url"),
                    page_number=primary_chunk.get("page_number") or meta.get("page_number"),
                    description=meta["title"],
                    snippet=snippet,
                    similarity_score=eval_result["retrieval_score"],
                    aligned_attributes=eval_result["aligned_attributes"],
                    eligibility_status=eval_result["eligibility_status"],
                    recommendation_score=eval_result["recommendation_score"],
                    retrieval_score=eval_result["retrieval_score"],
                    eligibility_evidence_score=eval_result["eligibility_evidence_score"],
                    profile_alignment_score=eval_result["profile_alignment_score"],
                    why_it_matches=eval_result["why_it_matches"],
                    key_eligibility_criteria=eval_result["key_eligibility_criteria"],
                    benefits_available=eval_result["benefits_available"],
                    required_documents=eval_result["required_documents"],
                    application_process=eval_result["application_process"],
                    unmet_or_conflicting_conditions=eval_result["unmet_or_conflicting_conditions"],
                    insufficient_evidence_notes=eval_result["insufficient_evidence_notes"],
                    # Fix 1 — pass document_id and source_id for compliance pinning
                    document_id=meta.get("document_id"),
                    source_id=primary_chunk.get("source_id"),
                )
            )

        # 4. Sort by status priority, recommendation score, and retrieval score
        discovered.sort(
            key=lambda x: (
                x.recommendation_score,
                1 if x.knowledge_type.upper() == "SCHEME" else 0,
                status_priority.get(x.eligibility_status, 0),
                x.similarity_score,
            ),
            reverse=True,
        )

        response = SchemeDiscoveryResponse(
            business_name=business_name,
            msme_classification=msme_class,
            attributes=attributes,
            total_discovered=len(discovered),
            schemes=discovered,
        )

        # Store in cache
        _DISCOVERY_CACHE[cache_key] = (now, response)
        # Limit cache size
        if len(_DISCOVERY_CACHE) > 200:
            oldest_key = min(_DISCOVERY_CACHE.keys(), key=lambda k: _DISCOVERY_CACHE[k][0])
            _DISCOVERY_CACHE.pop(oldest_key, None)

        return response

    async def query_rag_assistant(
        self,
        payload: SchemeQueryRequest,
        profile: Optional[ProfileModel] = None,
    ) -> SchemeQueryResponse:
        # Check query cache for anonymous, non-interactive queries
        is_personalized = bool(profile or payload.conversation_history or payload.current_scheme_id)
        clean_q = payload.query.strip().lower()
        chat_cache_key = f"{clean_q}_{payload.top_k or 5}_{payload.knowledge_type or 'all'}"
        now = time.time()
        if not is_personalized and chat_cache_key in _CHAT_CACHE:
            ts, cached_chat = _CHAT_CACHE[chat_cache_key]
            if now - ts < _CACHE_TTL:
                logger.info("Serving chat assistant response from cache for: %s", clean_q[:40])
                return cached_chat

        advisor = AdvisorService(schemes_service=self, rag_client=self.rag_client)
        advisor_res = await advisor.generate_personalized_response(
            query=payload.query,
            profile=profile,
            history=payload.conversation_history,
            current_scheme_id=payload.current_scheme_id,
        )

        citations = advisor_res.get("citations", [])
        response = SchemeQueryResponse(
            query=advisor_res.get("query", payload.query),
            answer_text=advisor_res.get("answer_text", ""),
            has_sufficient_context=advisor_res.get("has_sufficient_context", False),
            citations=citations,
            retrieved_result_count=advisor_res.get("retrieved_result_count", len(citations)),
            intent=advisor_res.get("intent"),
            recommended_schemes=advisor_res.get("recommended_schemes"),
            eligibility_gaps=advisor_res.get("eligibility_gaps"),
            next_steps=advisor_res.get("next_steps"),
            requires_clarification=advisor_res.get("requires_clarification", False),
        )

        if not is_personalized:
            _CHAT_CACHE[chat_cache_key] = (now, response)
            if len(_CHAT_CACHE) > 200:
                oldest_chat = min(_CHAT_CACHE.keys(), key=lambda k: _CHAT_CACHE[k][0])
                _CHAT_CACHE.pop(oldest_chat, None)

        return response

