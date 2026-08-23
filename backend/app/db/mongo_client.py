"""
Motor (async Mongo) client lifecycle.

connect_to_mongo() / close_mongo_connection() are called from main.py's
lifespan handler. get_database() is used by the FastAPI dependency in
api/v1/deps.py — nothing outside app/db ever talks to Motor directly.
"""
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client[settings.mongo_db_name]
    logger.info("Connected to MongoDB database '%s'", settings.mongo_db_name)


async def close_mongo_connection() -> None:
    global _client
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized — connect_to_mongo() must run at startup")
    return _db
