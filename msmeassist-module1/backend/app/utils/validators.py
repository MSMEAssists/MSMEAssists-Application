"""Format validators used by Pydantic schemas (app/schemas/*)."""
import re

PIN_CODE_RE = re.compile(r"^\d{6}$")
MOBILE_RE = re.compile(r"^\+91[6-9]\d{9}$")
PAN_RE = re.compile(r"^[A-Z]{5}\d{4}[A-Z]$")
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def is_valid_pin_code(value: str) -> bool:
    return bool(PIN_CODE_RE.match(value))


def is_valid_mobile(value: str) -> bool:
    return bool(MOBILE_RE.match(value))


def is_valid_pan(value: str) -> bool:
    return bool(PAN_RE.match(value.upper()))


def is_valid_gstin(value: str) -> bool:
    return bool(GSTIN_RE.match(value.upper()))


def password_strength_ok(value: str) -> bool:
    """Minimum bar: 8+ chars, at least one letter and one digit."""
    if len(value) < 8:
        return False
    has_letter = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)
    return has_letter and has_digit
