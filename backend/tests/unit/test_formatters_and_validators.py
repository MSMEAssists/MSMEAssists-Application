from app.utils.formatters import format_inr, mask_identifier
from app.utils.validators import is_valid_gstin, is_valid_mobile, is_valid_pan, is_valid_pin_code, password_strength_ok


def test_mask_identifier_keeps_prefix_and_suffix():
    masked = mask_identifier("UDYAM-TS-03-0012345")
    assert masked.startswith("UDYA")
    assert masked.endswith("45")
    assert "●" in masked
    assert "0012345" not in masked  # raw identifier never leaks


def test_mask_identifier_never_returns_raw_value():
    raw = "AABCU9603R"
    masked = mask_identifier(raw)
    assert masked != raw


def test_mask_identifier_short_string():
    assert mask_identifier("AB") == "●●"
    assert mask_identifier("") == ""


def test_format_inr_grouping():
    assert format_inr(1150000) == "₹ 11,50,000"
    assert format_inr(38500000) == "₹ 3,85,00,000"
    assert format_inr(500) == "₹ 500"


def test_pin_code_validation():
    assert is_valid_pin_code("500108") is True
    assert is_valid_pin_code("5001") is False
    assert is_valid_pin_code("abcdef") is False


def test_mobile_validation():
    assert is_valid_mobile("+919845012345") is True
    assert is_valid_mobile("9845012345") is False
    assert is_valid_mobile("+911234567890") is False  # must start with 6-9


def test_pan_and_gstin_validation():
    assert is_valid_pan("ABCDE1234F") is True
    assert is_valid_pan("invalid") is False
    assert is_valid_gstin("36AABCU9603R1ZM") is True
    assert is_valid_gstin("invalid") is False


def test_password_strength():
    assert password_strength_ok("Meridian@2026") is True
    assert password_strength_ok("short1") is False
    assert password_strength_ok("alllettersnodigits") is False
