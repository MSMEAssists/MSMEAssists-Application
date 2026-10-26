"""FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""

from app.unified_main import app

__all__ = ["app"]

