"""
FastAPI application entrypoint for Module 3: Explainable AI Recommendation Engine.

Run with:
  uvicorn app.main:app --reload --port 8002
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Explainable AI Recommendation Engine using Pairwise Comparisons, Bradley-Terry-Luce (BTL) Model, and Maximum Likelihood Estimation (MLE).",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware supporting localhost and 127.0.0.1 on any port
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "port": settings.module_port,
        "llm_provider": settings.llm_provider,
    }
