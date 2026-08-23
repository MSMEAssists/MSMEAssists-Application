"""
Enums shared across the models / schemas / services layers.

These mirror docs/module-1-api.md and docs/module-2-integration.md exactly.
New values may be appended (additive change); existing values must never be
renamed or removed without a documented Module 2 contract version bump.
"""
from enum import Enum


class UserRole(str, Enum):
    MSME_OWNER = "msme_owner"
    ADMIN = "admin"


class ProfileStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    ACTIVE = "active"


class BusinessType(str, Enum):
    MANUFACTURING = "manufacturing"
    SERVICES = "services"
    TRADING = "trading"
    OTHER = "other"


class AreaType(str, Enum):
    RURAL = "rural"
    URBAN = "urban"


class PremisesType(str, Enum):
    OWN = "own"
    RENTED = "rented"
    INDUSTRIAL_ESTATE = "industrial_estate"
    SHARED = "shared"


class ProfitabilityStatus(str, Enum):
    PROFITABLE = "profitable"
    BREAK_EVEN = "break_even"
    LOSS = "loss"


class MSMEClassification(str, Enum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    NOT_CLASSIFIED = "not_classified"


class SocialCategory(str, Enum):
    GENERAL = "general"
    SC = "sc"
    ST = "st"
    OBC = "obc"
    OTHER = "other"


class RegistrationType(str, Enum):
    UDYAM = "udyam"
    GST = "gst"
    PAN = "pan"
    FSSAI = "fssai"
    IEC = "iec"
    FACTORY_LICENSE = "factory_license"
    TRADE_LICENSE = "trade_license"
    POLLUTION_NOC = "pollution_noc"
    OTHER = "other"


class RegistrationStatus(str, Enum):
    REGISTERED = "registered"
    NOT_REGISTERED = "not_registered"
    IN_PROGRESS = "in_progress"
    NOT_APPLICABLE = "not_applicable"


class DocumentType(str, Enum):
    UDYAM_CERTIFICATE = "udyam_certificate"
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    FACTORY_LICENSE = "factory_license"
    TRADE_LICENSE = "trade_license"
    OTHER = "other"


class DocumentStatus(str, Enum):
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class StorageBackend(str, Enum):
    LOCAL = "local"
    S3 = "s3"


class AuditAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    SUBMITTED = "submitted"


ALLOWED_DOCUMENT_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}

PROFILE_SECTIONS = ["business", "location", "financial", "characteristics", "registrations", "documents"]
