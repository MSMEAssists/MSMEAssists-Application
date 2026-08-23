"""
Index creation, run once at application startup.

Mirrors the indexes documented in docs/architecture.md §3. Motor's
create_index is idempotent — safe to call on every startup.
"""
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    # users
    await db.users.create_index("email", unique=True)
    await db.users.create_index("mobile_number", unique=True)

    # business_profiles
    await db.business_profiles.create_index("user_id", unique=True)
    await db.business_profiles.create_index([("location.state", 1), ("location.district", 1)])
    await db.business_profiles.create_index("financial.msme_classification")
    await db.business_profiles.create_index("registrations.type")

    # documents
    await db.documents.create_index("user_id")
    await db.documents.create_index([("profile_id", 1), ("document_type", 1)])

    # profile_audit_logs
    await db.profile_audit_logs.create_index([("profile_id", 1), ("created_at", -1)])

    logger.info("MongoDB indexes ensured")
