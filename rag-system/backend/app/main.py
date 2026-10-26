from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start automated 24-hour background ingestion scheduler
    await scheduler.start()
    yield
    # Shutdown: Stop scheduler task cleanly
    await scheduler.stop()


app = FastAPI(
    title="Standalone Government Information RAG",
    description=(
        "Retrieves government scheme/loan/policy information exclusively "
        "from approved official government sources, with mandatory "
        "source provenance on every answer."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
