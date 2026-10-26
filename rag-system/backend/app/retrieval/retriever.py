"""
Query / Retrieval pipeline with Hybrid Retrieval:

  User Question -> Query Processing -> Dense Vector Search + Lexical TF-IDF Search +
  Exact-Term/Acronym Boosting -> Score Fusion -> Metadata Filtering -> Top-K -> Provenance Resolution
"""
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.db.repository import SQLiteRepository
from app.embeddings.embedding_service import EmbeddingService
from app.vectorstore.base import VectorStore


@dataclass
class RetrievedResult:
    chunk_id: str
    document_id: str
    knowledge_id: Optional[str]
    text: str
    similarity_score: float
    title: Optional[str]
    knowledge_type: str
    source_organization: str
    official_url: str
    page_number: Optional[int]
    publication_date: Optional[str]
    last_updated_date: Optional[str]
    official_application_url: Optional[str] = None


def process_query(raw_query: str) -> str:
    """Light query normalization -- trims, collapses whitespace. Kept
    separate from embedding so query rewriting/expansion can be added here
    later without touching the rest of the pipeline."""
    return re.sub(r"\s+", " ", raw_query).strip()


from app.processors.cleaner import is_junk_chunk

# Stopwords, generic inquiry terms, and high-frequency structural terms
# that must NEVER receive exact-term or keyword boosts on their own.
_GENERIC_QUERY_WORDS = {
    # Pronouns, auxiliaries, prepositions, articles
    "what", "which", "where", "when", "how", "who", "whom", "whose", "why",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "shall", "should", "will", "would",
    "may", "might", "must", "the", "a", "an", "and", "or", "but", "in", "on",
    "at", "to", "for", "of", "with", "by", "from", "up", "about", "into", "over",
    "after", "under", "above", "any", "some", "all", "each", "every", "other",
    "this", "that", "these", "those", "there", "their", "them", "then", "than",
    # Generic inquiry verbs & adjectives
    "available", "support", "scheme", "schemes", "program", "programs",
    "programme", "programmes", "guideline", "guidelines", "detail", "details",
    "information", "eligible", "eligibility", "benefit", "benefits", "document",
    "documents", "provide", "provided", "government", "central", "sector",
    "state", "national", "official", "portal", "website", "rule", "rules",
    "apply", "applying", "application", "process", "procedure", "need", "needed",
    "registered", "registration", "help", "tell", "know", "want", "require",
    "required", "requirement", "requirements", "guidance", "check", "give", "given",
    "good", "best", "new", "get", "getting", "year", "years", "time", "date",
    "take", "taking", "show", "showing", "explain", "without",
    # High-frequency structural words that appear across most MSME / financial documents
    "tax", "rate", "rates", "india", "indian", "loan", "loans", "credit", "finance",
    "financial", "assistance", "fund", "funds", "funding", "business", "businesses",
    "enterprise", "enterprises", "unit", "units", "msme", "msmes", "cost", "amount",
    "percentage", "percent", "limit", "ceiling", "service", "services", "work",
    "company", "companies", "firm", "firms", "bank", "banks", "commercial",
}


def extract_exact_query_terms(query: str) -> Tuple[Set[str], List[str]]:
    """Extract distinct scheme names, acronyms, and specialized substantive terms
    from the user's query.
    
    Returns:
      (acronyms_and_schemes, substantive_terms)
    """
    acronyms: Set[str] = set()
    substantive: List[str] = []
    
    for token in re.findall(r"\b[A-Za-z0-9&-]{2,}\b", query):
        lower_token = token.lower()
        if lower_token in _GENERIC_QUERY_WORDS:
            continue
        if (token.isupper() or "-" in token) and lower_token not in ("msme", "in"):
            acronyms.add(lower_token)
        if len(lower_token) >= 3 and lower_token not in _GENERIC_QUERY_WORDS:
            substantive.append(lower_token)
            
    return acronyms, substantive


class Retriever:
    def __init__(
        self,
        repository: SQLiteRepository,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
    ):
        self.repository = repository
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self._lexical_vectorizer: Optional[TfidfVectorizer] = None
        self._lexical_matrix = None
        self._lexical_chunks: List[Dict[str, Any]] = []
        self._lexical_chunk_ids: List[str] = []
        self._chunk_id_to_idx: Dict[str, int] = {}
        self._precomputed_lower_text: List[str] = []
        self._precomputed_lower_title: List[str] = []
        self._lexical_corpus_hash: Optional[int] = None
        self._chunk_meta_cache: Dict[str, Any] = {}
        self._query_cache: Dict[str, Tuple[float, List[RetrievedResult]]] = {}

    def _ensure_lexical_index(self) -> None:
        """Build or load in-memory lexical TF-IDF index across all repository chunks."""
        import pickle
        from pathlib import Path

        if self._lexical_matrix is not None:
            return

        lexical_cache_path = Path(self.repository.path).parent / "lexical_index.pkl"
        if lexical_cache_path.exists():
            try:
                with open(lexical_cache_path, "rb") as f:
                    saved = pickle.load(f)
                    self._lexical_vectorizer = saved["vectorizer"]
                    self._lexical_matrix = saved["matrix"]
                    self._lexical_chunks = saved["chunks"]
                    self._lexical_chunk_ids = saved["chunk_ids"]
                    self._chunk_id_to_idx = saved["chunk_id_to_idx"]
                    self._precomputed_lower_text = saved["precomputed_lower_text"]
                    self._precomputed_lower_title = saved["precomputed_lower_title"]
                    self._lexical_corpus_hash = saved["corpus_hash"]
                    return
            except Exception:
                pass

        chunks = self.repository._list("chunks") if hasattr(self.repository, "_list") else []
        current_hash = len(chunks)

        if not chunks:
            self._lexical_vectorizer = None
            self._lexical_matrix = None
            self._lexical_chunks = []
            self._lexical_chunk_ids = []
            self._chunk_id_to_idx = {}
            self._precomputed_lower_text = []
            self._precomputed_lower_title = []
            self._lexical_corpus_hash = 0
            return

        texts = [c.get("text", "") for c in chunks]
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            token_pattern=r"(?u)\b[\w-]+\b",
        )
        matrix = vectorizer.fit_transform(texts)

        self._lexical_vectorizer = vectorizer
        self._lexical_matrix = matrix
        self._lexical_chunks = chunks
        self._lexical_chunk_ids = [c["chunk_id"] for c in chunks]
        self._chunk_id_to_idx = {c["chunk_id"]: idx for idx, c in enumerate(chunks)}
        self._precomputed_lower_text = [c.get("text", "").lower() for c in chunks]
        self._precomputed_lower_title = [(c.get("title") or "").lower() for c in chunks]
        self._lexical_corpus_hash = current_hash
        self._query_cache.clear()

        try:
            with open(lexical_cache_path, "wb") as f:
                pickle.dump(
                    {
                        "vectorizer": self._lexical_vectorizer,
                        "matrix": self._lexical_matrix,
                        "chunks": self._lexical_chunks,
                        "chunk_ids": self._lexical_chunk_ids,
                        "chunk_id_to_idx": self._chunk_id_to_idx,
                        "precomputed_lower_text": self._precomputed_lower_text,
                        "precomputed_lower_title": self._precomputed_lower_title,
                        "corpus_hash": self._lexical_corpus_hash,
                    },
                    f,
                    protocol=pickle.HIGHEST_PROTOCOL,
                )
        except Exception:
            pass

    def search(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None,
        knowledge_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> List[RetrievedResult]:
        top_k = top_k or settings.default_top_k
        similarity_threshold = (
            similarity_threshold if similarity_threshold is not None else settings.similarity_threshold
        )

        processed_query = process_query(query)

        # Check LRU Query Cache (TTL: 300 seconds)
        cache_key = f"{processed_query}|{top_k}|{similarity_threshold}|{knowledge_type}|{source_id}"
        now = time.time()
        if cache_key in self._query_cache:
            cached_time, cached_res = self._query_cache[cache_key]
            if now - cached_time < 300.0:
                return cached_res

        filters: Dict[str, str] = {}
        if knowledge_type:
            filters["knowledge_type"] = knowledge_type
        if source_id:
            filters["source_id"] = source_id

        if settings.hybrid_retrieval_enabled:
            results = self._hybrid_search(
                query=processed_query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
            )
        else:
            results = self._dense_search(
                query=processed_query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                filters=filters,
            )

        # Store in cache (cap at 500 queries)
        if len(self._query_cache) > 500:
            oldest_key = min(self._query_cache.keys(), key=lambda k: self._query_cache[k][0])
            self._query_cache.pop(oldest_key, None)
        self._query_cache[cache_key] = (now, results)

        return results

    def _dense_search(
        self,
        query: str,
        top_k: int,
        similarity_threshold: float,
        filters: Dict[str, str],
    ) -> List[RetrievedResult]:
        query_embedding = self.embedding_service.embed([query]).vectors[0]
        hits = self.vector_store.search(query_embedding, top_k=top_k, filters=filters or None)

        results: List[RetrievedResult] = []
        for hit in hits:
            if hit.score < similarity_threshold:
                continue
            res = self._build_retrieved_result(hit.chunk_id, hit.score)
            if res:
                results.append(res)

        self._log_retrieval(query, top_k, similarity_threshold, filters, len(results))
        return results

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        similarity_threshold: float,
        filters: Dict[str, str],
    ) -> List[RetrievedResult]:
        self._ensure_lexical_index()

        # 1. Dense scoring
        query_embedding = self.embedding_service.embed([query]).vectors[0]
        dense_hits = self.vector_store.search(query_embedding, top_k=min(self.vector_store.count() or 100, 300))
        dense_score_map = {h.chunk_id: max(0.0, h.score) for h in dense_hits}

        # 2. Lexical scoring
        lex_sims = None
        if self._lexical_vectorizer is not None and self._lexical_matrix is not None:
            q_lex_vec = self._lexical_vectorizer.transform([query])
            lex_sims = (q_lex_vec @ self._lexical_matrix.T).toarray()[0]

        # 3. Exact query terms & acronyms
        acronyms, substantive_terms = extract_exact_query_terms(query)
        dense_w = settings.hybrid_dense_weight
        lex_w = settings.hybrid_lexical_weight
        boost_w = settings.hybrid_exact_boost_weight

        # 4. Out-of-domain validation:
        # If user asks about an entity/topic (>= 4 chars) that has zero presence across the corpus,
        # return empty results rather than leaking unrelated documents.
        if substantive_terms and self._precomputed_lower_text:
            out_of_domain = all(
                sum(1 for txt in self._precomputed_lower_text if term in txt) == 0
                for term in substantive_terms
                if len(term) >= 4
            )
            if out_of_domain:
                self._log_retrieval(query, top_k, similarity_threshold, filters, 0)
                return []

        # 5. Candidate generation: dense hits + top 400 lexical hits + direct acronym index hits
        candidate_indices = set()
        if dense_score_map:
            for cid, sc in dense_score_map.items():
                if sc > 0.05 and cid in self._chunk_id_to_idx:
                    candidate_indices.add(self._chunk_id_to_idx[cid])

        if lex_sims is not None and len(lex_sims) > 0:
            top_n = min(400, len(lex_sims))
            top_lex_part = np.argpartition(lex_sims, -top_n)[-top_n:]
            for idx in top_lex_part:
                if lex_sims[idx] > 0.01:
                    candidate_indices.add(int(idx))

        # Direct acronym / scheme lookups to guarantee official circular inclusion
        for acr in acronyms:
            for idx, (t_low, tit_low) in enumerate(zip(self._precomputed_lower_text, self._precomputed_lower_title)):
                if acr in tit_low or acr in t_low:
                    candidate_indices.add(idx)

        if not candidate_indices:
            candidate_indices = range(min(50, len(self._lexical_chunks)))

        candidates: List[Tuple[float, str, str, str]] = []

        # 6. Evaluate candidates against filters, junk rejection, and score fusion
        for idx in candidate_indices:
            chunk = self._lexical_chunks[idx]
            chunk_id = self._lexical_chunk_ids[idx]
            c_text = chunk.get("text", "")
            c_title = chunk.get("title") or ""
            c_url = chunk.get("official_url") or ""

            # Purge junk chunks (login forms, TOC dot leaders, photo galleries, binary docs)
            if is_junk_chunk(c_text, c_url, c_title):
                continue

            # Filter checks
            if "source_id" in filters and chunk.get("source_id") != filters["source_id"]:
                continue
            if "knowledge_type" in filters:
                kt = chunk.get("knowledge_type")
                if hasattr(kt, "value"):
                    kt = kt.value
                if kt != filters["knowledge_type"]:
                    continue

            c_text_lower = self._precomputed_lower_text[idx]
            c_title_lower = self._precomputed_lower_title[idx]

            # Substantive term coverage check: candidate chunk must match at least one substantive term
            if substantive_terms:
                matched_sub = sum(1 for term in substantive_terms if term in c_text_lower or term in c_title_lower)
                if matched_sub == 0:
                    continue
                coverage_ratio = matched_sub / len(substantive_terms)
            else:
                coverage_ratio = 1.0

            d_score = dense_score_map.get(chunk_id, 0.0)
            l_score = float(lex_sims[idx]) if lex_sims is not None else 0.0

            # Scheme title boost (prioritize official circulars where title explicitly names scheme)
            title_boost = 0.0
            for acr in acronyms:
                if acr in c_title_lower:
                    title_boost += 0.35
                elif acr in c_text_lower:
                    title_boost += 0.15

            for term in substantive_terms:
                if term in c_title_lower:
                    title_boost += 0.10

            hybrid_score = (dense_w * d_score) + (lex_w * l_score) + min(title_boost, 0.40) + (0.10 * coverage_ratio)

            if hybrid_score >= similarity_threshold:
                candidates.append((hybrid_score, chunk_id, chunk["document_id"], c_text))

        # Sort candidates descending by hybrid_score
        candidates.sort(key=lambda x: -x[0])

        # 7. Document Diversity and Deduplication
        results: List[RetrievedResult] = []
        doc_counts: Dict[str, int] = {}
        seen_words: List[Set[str]] = []

        for score, chunk_id, doc_id, text in candidates:
            # Enforce max 2 chunks per document to prevent single playbook dominance
            if doc_counts.get(doc_id, 0) >= 2:
                continue

            # Jaccard deduplication to eliminate verbatim duplicate paragraphs
            words = set(re.findall(r"\w{4,}", text.lower()))
            is_duplicate = False
            for prev_words in seen_words:
                inter = len(words & prev_words)
                union = len(words | prev_words)
                if union > 0 and (inter / union) > 0.65:
                    is_duplicate = True
                    break
            if is_duplicate:
                continue

            res = self._build_retrieved_result(chunk_id, score)
            if res:
                results.append(res)
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
                seen_words.append(words)

            if len(results) >= top_k:
                break

        self._log_retrieval(query, top_k, similarity_threshold, filters, len(results))
        return results

    def _build_retrieved_result(self, chunk_id: str, score: float) -> Optional[RetrievedResult]:
        cached = self._chunk_meta_cache.get(chunk_id)
        if cached:
            # Clone with current similarity score
            return RetrievedResult(
                chunk_id=cached.chunk_id,
                document_id=cached.document_id,
                knowledge_id=cached.knowledge_id,
                text=cached.text,
                similarity_score=score,
                title=cached.title,
                knowledge_type=cached.knowledge_type,
                source_organization=cached.source_organization,
                official_url=cached.official_url,
                page_number=cached.page_number,
                publication_date=cached.publication_date,
                last_updated_date=cached.last_updated_date,
                official_application_url=cached.official_application_url,
            )

        chunk = self.repository.get_chunk(chunk_id)
        if not chunk:
            return None
        document = self.repository.get_document(chunk["document_id"])
        if not document:
            return None

        knowledge_item = None
        if chunk.get("knowledge_id"):
            knowledge_item = self.repository.get_knowledge_item(chunk["knowledge_id"])

        doc_title = document.get("title")
        chunk_title = chunk.get("title")
        if doc_title and (
            not chunk_title
            or chunk_title.lower().startswith("microsoft word")
            or chunk_title.lower().endswith(".cdr")
            or chunk_title.lower() in ("untitled", "none")
        ):
            final_title = doc_title
        else:
            final_title = chunk_title or doc_title

        app_url = None
        if knowledge_item and isinstance(knowledge_item, dict) and knowledge_item.get("official_application_url"):
            app_url = knowledge_item.get("official_application_url")
        elif document.get("url"):
            try:
                from app.core.local_documents import LOCAL_PDF_REGISTRY
            except Exception:
                LOCAL_PDF_REGISTRY = {}
            local_meta = next((v for v in LOCAL_PDF_REGISTRY.values() if getattr(v, "official_url", None) == document["url"]), None)
            if local_meta and getattr(local_meta, "official_application_url", None):
                app_url = local_meta.official_application_url

        try:
            from app.core.url_validator import verify_direct_application_url
            verified_app_url = verify_direct_application_url(app_url)
        except Exception:
            verified_app_url = app_url

        built = RetrievedResult(
            chunk_id=chunk["chunk_id"],
            document_id=chunk["document_id"],
            knowledge_id=chunk.get("knowledge_id"),
            text=chunk["text"],
            similarity_score=score,
            title=final_title,
            knowledge_type=chunk["knowledge_type"],
            source_organization=document["organization"],
            official_url=document["url"],
            page_number=chunk.get("page_number"),
            publication_date=document.get("publication_date"),
            last_updated_date=document.get("last_updated_date"),
            official_application_url=verified_app_url,
        )
        self._chunk_meta_cache[chunk_id] = built
        return built

    def _log_retrieval(
        self,
        query: str,
        top_k: int,
        similarity_threshold: float,
        filters: Dict[str, str],
        result_count: int,
    ) -> None:
        self.repository.add_retrieval_log(
            {
                "query": query,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "knowledge_type": filters.get("knowledge_type"),
                "source_id": filters.get("source_id"),
                "result_count": result_count,
                "timestamp": time.time(),
            }
        )
