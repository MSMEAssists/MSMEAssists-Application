import sys
from pathlib import Path
import importlib.util

# Forward to rag-system/backend/app/core/local_documents
_rag_core = Path(__file__).resolve().parents[4] / "rag-system" / "backend" / "app" / "core"

try:
    _spec = importlib.util.spec_from_file_location("_rag_local_documents", str(_rag_core / "local_documents.py"))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    LOCAL_PDF_REGISTRY = _mod.LOCAL_PDF_REGISTRY
    get_local_document_metadata = _mod.get_local_document_metadata
    LocalDocumentMetadata = getattr(_mod, "LocalDocumentMetadata", None)
except Exception as _e:
    LOCAL_PDF_REGISTRY = {}
    def get_local_document_metadata(f): return None
    LocalDocumentMetadata = None
