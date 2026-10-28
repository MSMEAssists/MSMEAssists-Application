import sys
from pathlib import Path
import importlib.util

# Forward to rag-system/backend/app/core/scheme_portal_registry
_rag_core = Path(__file__).resolve().parents[4] / "rag-system" / "backend" / "app" / "core"

try:
    _spec = importlib.util.spec_from_file_location(
        "_rag_scheme_portal_registry",
        str(_rag_core / "scheme_portal_registry.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules["_rag_scheme_portal_registry"] = _mod
    _spec.loader.exec_module(_mod)

    CANONICAL_SCHEME_REGISTRY = _mod.CANONICAL_SCHEME_REGISTRY
    SchemePortalMetadata = _mod.SchemePortalMetadata
    match_canonical_scheme = _mod.match_canonical_scheme
    extract_candidate_application_urls = _mod.extract_candidate_application_urls
    resolve_scheme_metadata = _mod.resolve_scheme_metadata
except Exception as _e:
    CANONICAL_SCHEME_REGISTRY = {}
    SchemePortalMetadata = None
    def match_canonical_scheme(*args, **kwargs): return None
    def extract_candidate_application_urls(*args, **kwargs): return []
    def resolve_scheme_metadata(*args, **kwargs): return None
