"""
Orchestrates Pipeline 2 (Query/Retrieval) plus the RAG answer-generation
layer for the /api/rag/query endpoint. /api/retrieval/search uses just the
Retriever directly (raw retrieval results, no answer generation).
"""
from typing import Optional

from app.db.repository import SQLiteRepository
from app.embeddings.embedding_service import EmbeddingService
from app.rag.answer_generator import LLMClient, RagAnswer, generate_answer
from app.retrieval.retriever import Retriever
from app.vectorstore.base import VectorStore


class QueryService:
    def __init__(
        self,
        repository: SQLiteRepository,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        llm_client: Optional[LLMClient] = None,
    ):
        self.retriever = Retriever(repository, vector_store, embedding_service)
        self.llm_client = llm_client

    def rag_query(
        self,
        query: str,
        top_k: int = None,
        similarity_threshold: float = None,
        knowledge_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> RagAnswer:
        results = self.retriever.search(
            query, top_k=top_k, similarity_threshold=similarity_threshold,
            knowledge_type=knowledge_type, source_id=source_id,
        )
        return generate_answer(query, results, llm_client=self.llm_client)
