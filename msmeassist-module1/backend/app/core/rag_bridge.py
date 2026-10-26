"""
In-process bridge to the Government Knowledge RAG Service.

Allows Module 1 and Module 5 to directly query the RAG service in-memory
when running unified on port 8000, eliminating loopback HTTP network overhead,
timeouts, and connection contention while falling back to HTTP if decoupled.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_QUERY_SERVICE = None


def set_inprocess_query_service(service):
    """Explicitly register the warmed RAG QueryService singleton."""
    global _QUERY_SERVICE
    _QUERY_SERVICE = service
    logger.info("⚡ In-process RAG QueryService registered successfully into rag_bridge.")


def get_inprocess_query_service():
    """Retrieve or initialize the in-process RAG QueryService singleton."""
    global _QUERY_SERVICE
    if _QUERY_SERVICE is not None:
        return _QUERY_SERVICE

    try:
        project_root = Path(__file__).resolve().parents[4]
        rag_root = project_root / "rag-system" / "backend"
        if not rag_root.exists():
            return None

        os.environ.setdefault("SQLITE_PATH", str(rag_root / "data" / "gov_rag.db"))
        os.environ.setdefault("VECTOR_STORE_PATH", str(rag_root / "data" / "vector_store"))
        os.environ.setdefault("SOURCE_DOCUMENTS_PATH", str(rag_root / "data" / "source_documents"))

        root_pkg_path = rag_root / "app" / "__init__.py"
        if not root_pkg_path.exists():
            return None

        import importlib.util
        original_app = sys.modules.get("app")
        original_submodules = {k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")}
        original_sys_path = list(sys.path)
        sys.path.insert(0, str(rag_root))

        for key in list(sys.modules):
            if key == "app" or key.startswith("app."):
                sys.modules.pop(key, None)

        spec = importlib.util.spec_from_file_location(
            "app",
            root_pkg_path,
            submodule_search_locations=[str(rag_root / "app")],
        )
        if spec is None or spec.loader is None:
            return None

        package = importlib.util.module_from_spec(spec)
        sys.modules["app"] = package
        try:
            spec.loader.exec_module(package)
            deps_mod = __import__("app.api.deps", fromlist=["get_query_service"])
            _QUERY_SERVICE = deps_mod.get_query_service()
            logger.info("⚡ In-process RAG QueryService connected successfully.")
            return _QUERY_SERVICE
        finally:
            for key in list(sys.modules):
                if key == "app" or key.startswith("app."):
                    sys.modules.pop(key, None)
            if original_app is not None:
                sys.modules["app"] = original_app
            for key, value in original_submodules.items():
                if key not in sys.modules:
                    sys.modules[key] = value
            sys.path[:] = original_sys_path
    except Exception as exc:
        logger.warning("Could not initialize in-process RAG QueryService: %s", exc)
        return None


def inprocess_search(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.0,
    knowledge_type: Optional[str] = None,
    source_id: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Execute search directly against the in-memory RAG retriever."""
    qs = get_inprocess_query_service()
    if qs is None:
        return None
    try:
        results = qs.retriever.search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            knowledge_type=knowledge_type,
            source_id=source_id,
        )
        return [r.__dict__ for r in results]
    except Exception as e:
        logger.warning("In-process RAG search failed: %s", e)
        return None


def inprocess_rag_query(
    query: str,
    top_k: int = 5,
    similarity_threshold: Optional[float] = None,
    knowledge_type: Optional[str] = None,
    source_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Execute complete RAG answer generation directly in-memory."""
    qs = get_inprocess_query_service()
    if qs is None:
        return None
    try:
        answer = qs.rag_query(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            knowledge_type=knowledge_type,
            source_id=source_id,
        )
        return {
            "query": answer.query,
            "answer_text": answer.answer_text,
            "has_sufficient_context": answer.has_sufficient_context,
            "citations": [c.__dict__ for c in answer.citations],
            "retrieved_result_count": answer.retrieved_result_count,
        }
    except Exception as e:
        logger.warning("In-process RAG answer generation failed: %s", e)
        return None
