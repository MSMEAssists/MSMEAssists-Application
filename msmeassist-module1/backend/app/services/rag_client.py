"""
HTTP client for the unified MSMEAssist backend.

In the single-localhost deployment, the RAG endpoints are served by the same app on
port 8000 rather than a separate standalone service on port 8001.
"""
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.utils.exceptions import AppError

logger = logging.getLogger(__name__)


class RagServiceUnavailableError(AppError):
    status_code = 503
    code = "RAG_SERVICE_UNAVAILABLE"

    def __init__(self, message: str = "Government Information RAG Service is currently unreachable"):
        super().__init__(message)


class RagClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 6.0):
        self.settings = get_settings()
        self.base_url = (base_url or self.settings.rag_api_base_url).rstrip("/")
        self.timeout = timeout

    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        knowledge_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        # 1. Try instantaneous in-process search
        try:
            from app.core.rag_bridge import inprocess_search
            direct_res = inprocess_search(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                knowledge_type=knowledge_type,
                source_id=source_id,
            )
            if direct_res is not None:
                return direct_res
        except Exception as e:
            logger.debug("In-process RAG search bypassed: %s", e)

        # 2. HTTP Fallback
        url = f"{self.base_url}/api/retrieval/search"
        payload = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "knowledge_type": knowledge_type,
            "source_id": source_id,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error("RAG search returned status %d: %s", resp.status_code, resp.text)
                    return []
                return resp.json()
        except httpx.RequestError as exc:
            logger.warning("Failed to connect to RAG service at %s: %s", url, exc)
            return []

    async def query_rag(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None,
        knowledge_type: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 1. Try instantaneous in-process RAG answer generation
        try:
            from app.core.rag_bridge import inprocess_rag_query
            direct_ans = inprocess_rag_query(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                knowledge_type=knowledge_type,
                source_id=source_id,
            )
            if direct_ans is not None:
                return direct_ans
        except Exception as e:
            logger.debug("In-process RAG query bypassed: %s", e)

        # 2. HTTP Fallback
        url = f"{self.base_url}/api/rag/query"
        payload = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold,
            "knowledge_type": knowledge_type,
            "source_id": source_id,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error("RAG query returned status %d: %s", resp.status_code, resp.text)
                    raise RagServiceUnavailableError(f"RAG service error: {resp.status_code}")
                return resp.json()
        except httpx.RequestError as exc:
            logger.warning("Failed to connect to RAG service at %s: %s", url, exc)
            raise RagServiceUnavailableError()

    async def get_health(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()
                return {"status": "error", "code": resp.status_code}
        except httpx.RequestError:
            return {"status": "unavailable"}
