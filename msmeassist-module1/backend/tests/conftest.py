"""
Shared fixtures for the whole test suite.

Design choices:
  - Required env vars are set BEFORE any `app.*` module is imported, since
    Settings() is read at import time via get_settings().
  - Integration tests build a fresh FastAPI app per test (mirroring
    app.main's routers + exception handlers) with `get_db` overridden to
    an in-memory mongomock-motor database — no real MongoDB required.
  - Document storage is pointed at a pytest tmp_path so upload tests never
    touch a real filesystem location outside the test sandbox.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_DB_NAME", "msmeassist_test")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.api.v1.deps import get_db
from app.api.v1.routers import auth, documents, profile, schemes
from app.utils.exceptions import AppError
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _build_test_app() -> FastAPI:
    app = FastAPI()

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

    app.include_router(auth.router, prefix="/api")
    app.include_router(profile.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(schemes.router, prefix="/api")
    app.include_router(schemes.workflow_router, prefix="/api")
    return app


@pytest.fixture()
def mongo_db():
    client = AsyncMongoMockClient()
    return client["msmeassist_test"]


@pytest.fixture()
def app(mongo_db, tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.storage.factory import get_storage

    get_settings.cache_clear()
    get_storage.cache_clear()
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path / "documents"))
    get_settings.cache_clear()

    test_app = _build_test_app()
    test_app.dependency_overrides[get_db] = lambda: mongo_db
    yield test_app
    test_app.dependency_overrides.clear()
    get_storage.cache_clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def registered_user(client):
    payload = {
        "full_name": "Anita Rao",
        "email": "anita.rao@meridianfab.in",
        "mobile_number": "+919845012345",
        "password": "Meridian@2026",
        "confirm_password": "Meridian@2026",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"token": body["access_token"], "user": body["user"], "raw_payload": payload}


@pytest.fixture()
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['token']}"}
