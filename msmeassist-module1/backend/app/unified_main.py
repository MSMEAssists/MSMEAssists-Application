"""Unified MSMEAssist backend entrypoint.

This builds a single FastAPI app that exposes the Module 1 API, the Module 3
recommendation endpoints, and the government RAG routes from the separate
service folders while running from a single localhost port.
"""
from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routers import admin, auth, compliance, decision_intelligence, documents, export, profile, schemes
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.indexes import create_indexes
from app.db.mongo_client import close_mongo_connection, connect_to_mongo, get_database
from app.utils.exceptions import AppError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE3_ROOT = PROJECT_ROOT / "msmeassist-module3" / "backend"
RAG_ROOT = PROJECT_ROOT / "rag-system" / "backend"
MODULE4_ROOT = PROJECT_ROOT / "msmeassist-module4" / "backend"

get_settings.cache_clear()
settings = get_settings()


def _load_external_package(package_root: Path, extract_deps: bool = False) -> Any:
    """Load an external app package by path without clobbering the base app package.

    The Module 3 and RAG projects both use the package name "app", so we clear the
    active app package state before importing the external service package.
    """
    root_pkg_path = package_root / "app" / "__init__.py"
    if not root_pkg_path.exists():
        raise FileNotFoundError(f"Missing package root for {package_root}: {root_pkg_path}")

    original_app = sys.modules.get("app")
    original_submodules = {k: v for k, v in sys.modules.items() if k == "app" or k.startswith("app.")}
    original_sys_path = list(sys.path)
    sys.path.insert(0, str(package_root))

    for key in list(sys.modules):
        if key == "app" or key.startswith("app."):
            sys.modules.pop(key, None)

    spec = spec_from_file_location(
        "app",
        root_pkg_path,
        submodule_search_locations=[str(package_root / "app")],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load external app package from {root_pkg_path}")

    package = module_from_spec(spec)
    sys.modules["app"] = package
    qs = None
    try:
        spec.loader.exec_module(package)
        imported_module = __import__("app.api.routes", fromlist=["router"])
        if extract_deps:
            try:
                deps_mod = __import__("app.api.deps", fromlist=["get_query_service"])
                qs = deps_mod.get_query_service()
            except Exception as _e:
                _ext_logger.warning("Could not extract query service from %s: %s", package_root, _e)
        if extract_deps:
            return imported_module, qs
        return imported_module
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await connect_to_mongo()
    await create_indexes(get_database())
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description="Unified MSMEAssist API with profile, schemes, recommendations, and RAG capabilities.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "field": exc.field}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first_error.get("loc", [])[1:]) or None
    message = first_error.get("msg", "Invalid request payload")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "VALIDATION_ERROR", "message": message, "field": field}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    import logging as _log
    _log.getLogger(__name__).error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method, request.url.path, exc, traceback.format_exc()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred", "field": None}},
    )


# Existing Module 1 routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(schemes.router, prefix=settings.api_prefix)
app.include_router(schemes.workflow_router, prefix=settings.api_prefix)
app.include_router(compliance.router, prefix=settings.api_prefix)
app.include_router(export.router, prefix=settings.api_prefix)
app.include_router(decision_intelligence.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)

# Additional merged modules from their original project folders
# Each is wrapped in try/except so a missing dependency in one module
# never crashes Module 1 (auth, profile, documents) which must always work.

import logging as _logging
_ext_logger = _logging.getLogger(__name__)

try:
    module3_routes = _load_external_package(MODULE3_ROOT)
    app.include_router(module3_routes.router)
    _ext_logger.info("✅ Module 3 (AI Recommendations) loaded successfully.")
except Exception as _e:
    _ext_logger.warning(
        "⚠️  Module 3 could not be loaded (%s). "
        "Install its dependencies: cd msmeassist-module3/backend && pip install -r requirements.txt",
        _e,
    )

# The embedded RAG service uses relative paths by default. Resolve them against
# its own data directory so the unified app works from any current directory.
os.environ.setdefault("SQLITE_PATH", str(RAG_ROOT / "data" / "gov_rag.db"))
os.environ.setdefault("VECTOR_STORE_PATH", str(RAG_ROOT / "data" / "vector_store"))
os.environ.setdefault("SOURCE_DOCUMENTS_PATH", str(RAG_ROOT / "data" / "source_documents"))

try:
    rag_routes, rag_qs = _load_external_package(RAG_ROOT, extract_deps=True)
    app.include_router(rag_routes.router)
    if rag_qs is not None:
        from app.core.rag_bridge import set_inprocess_query_service
        set_inprocess_query_service(rag_qs)
    _ext_logger.info("✅ RAG System (Government Knowledge) loaded successfully & connected in-process.")
except Exception as _e:
    _ext_logger.warning(
        "⚠️  RAG System could not be loaded (%s). "
        "Install its dependencies: cd rag-system/backend && pip install -r requirements.txt",
        _e,
    )

try:
    module4_routes = _load_external_package(MODULE4_ROOT)
    app.include_router(module4_routes.router)
    _ext_logger.info("✅ Module 4 (Finance & Loan Agent) loaded successfully.")
except Exception as _e:
    _ext_logger.warning(
        "⚠️  Module 4 could not be loaded (%s). "
        "Install its dependencies: cd msmeassist-module4/backend && pip install -r requirements.txt",
        _e,
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
