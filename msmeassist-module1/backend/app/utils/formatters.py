"""
Formatting / masking helpers.

mask_identifier() is the single place responsible for making sure raw
registration identifiers (GSTIN, PAN, Udyam number, etc.) never leave
Module 1's boundary unmasked — see docs/module-2-integration.md.
"""


def mask_identifier(identifier: str, visible_prefix: int = 4, visible_suffix: int = 2, mask_char: str = "●") -> str:
    """
    Keeps a short visible prefix and suffix, masks the middle.
    e.g. "UDYAM-TS-03-0012345" -> "UDYA●●●●●●●●●●●●●●45"
    Short strings are masked entirely except the first/last char.
    """
    if not identifier:
        return identifier
    length = len(identifier)
    if length <= visible_prefix + visible_suffix:
        if length <= 2:
            return mask_char * length
        return identifier[0] + mask_char * (length - 2) + identifier[-1]
    prefix = identifier[:visible_prefix]
    suffix = identifier[-visible_suffix:]
    middle = mask_char * (length - visible_prefix - visible_suffix)
    return f"{prefix}{middle}{suffix}"


def format_inr(amount: float) -> str:
    """1150000 -> '₹ 11,50,000' (Indian digit grouping)."""
    amount_int = int(round(amount))
    sign = "-" if amount_int < 0 else ""
    amount_int = abs(amount_int)
    s = str(amount_int)
    if len(s) <= 3:
        grouped = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last3
    return f"{sign}₹ {grouped}"
