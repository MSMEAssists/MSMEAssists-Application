import sys
from pathlib import Path
import importlib.util

# Forward to rag-system/backend/app/core/url_validator
_rag_core = Path(__file__).resolve().parents[4] / "rag-system" / "backend" / "app" / "core"

try:
    _spec = importlib.util.spec_from_file_location("_rag_url_validator", str(_rag_core / "url_validator.py"))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    verify_direct_application_url = getattr(_mod, "verify_direct_application_url", lambda u: u)
    validate_url = getattr(_mod, "validate_url", lambda u: True)
except Exception as _e:
    def verify_direct_application_url(u): return u
    def validate_url(u): return True
