"""
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routers import auth, documents, profile
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.indexes import create_indexes
from app.db.mongo_client import close_mongo_connection, connect_to_mongo, get_database
from app.utils.exceptions import AppError

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await connect_to_mongo()
    await create_indexes(get_database())
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.app_name,
    description="Module 1 — Business Profile & Eligibility Engine API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------
# Global error handling — every error response follows the envelope
# documented in docs/module-1-api.md:
#   { "error": { "code": "...", "message": "...", "field": "..." } }
# ----------------------------------------------------------------------


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
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred", "field": None}},
    )


# ----------------------------------------------------------------------
# Routers
# ----------------------------------------------------------------------

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
