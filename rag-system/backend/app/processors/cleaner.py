"""
Cleaning and normalization.

Preserves meaning-bearing content (eligibility, financial values, dates,
conditions, application instructions, legal/policy language) while
removing whitespace noise, encoding artifacts, and repeated
headers/footers (common in paginated government PDFs).
"""
import html
import re
import unicodedata
from collections import Counter
from typing import List


def normalize_encoding(text: str) -> str:
    if not text:
        return ""
    # 1. Unescape HTML entities
    text = html.unescape(text)
    # 2. Unicode NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # 3. Mojibake and corrupted glyph replacements
    replacements = {
        "\ufffd": " ",   # Replacement character
        "\u00a0": " ",   # Non-breaking space
        "\u200b": "",    # Zero-width space
        "\ufeff": "",    # BOM
        "\u2018": "'",   # Left single quote
        "\u2019": "'",   # Right single quote
        "\u201c": '"',   # Left double quote
        "\u201d": '"',   # Right double quote
        "\u2013": "-",   # En dash
        "\u2014": " -- ",# Em dash (safe standard spacing)
        "\u2022": " - ", # Bullet point
        "\u25cf": " - ", # Black circle bullet
        "\u2023": " - ", # Triangular bullet
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€“": "-",
        "â€”": " -- ",
        "\x91": "'",
        "\x92": "'",
        "\x93": '"',
        "\x94": '"',
        "\x96": "-",
        "\x97": " -- ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # 4. Remove unprintable control characters and private-use font codes
    cleaned_chars = []
    for ch in text:
        code = ord(ch)
        # Private use area common in PDF font mappings
        if 0xE000 <= code <= 0xF8FF:
            continue
        # Disallow raw control codes except newline, carriage return, tab
        if code < 32 and ch not in ("\n", "\r", "\t"):
            continue
        if code == 127:
            continue
        cleaned_chars.append(ch)

    text = "".join(cleaned_chars)
    return text


_JUNK_PATTERNS = [
    r"forgot\s+password",
    r"login\s+screen",
    r"enter\s+(?:user\s*id|username|password)",
    r"session\s+expired",
    r"enter\s+captcha",
    r"portal\s+login",
    r"click\s+here\s+to\s+login",
]
_JUNK_RE = re.compile("|".join(_JUNK_PATTERNS), re.IGNORECASE)

_JUNK_URL_ENDINGS = (
    "/login.html",
    "/login.aspx",
    "/nbfclogin.html",
    "/userlogin.html",
    "/forgotpassword",
)


def is_junk_chunk(text: str, url: str = "", title: str = "") -> bool:
    """Detects whether a chunk contains authentication/login forms, table of contents dot leaders,
    or pure navigation boilerplate that lacks substantive factual content."""
    lower_url = (url or "").lower()
    for ending in _JUNK_URL_ENDINGS:
        if lower_url.endswith(ending):
            return True

    lower_title = (title or "").lower()
    if any(k in lower_title for k in ("login screen", "forgot password", "user login", "jfif", "pk !")):
        return True
    if "galleryphotos" in lower_url or "subgalleryphoto" in lower_url or "/galleryalbum/" in lower_url:
        return True

    if not text or len(text.strip()) < 35:
        return True

    lower_text = text.lower().strip()
    if lower_text.startswith("jfif") or lower_text.startswith("pk !"):
        return True

    lower_text = text.lower().strip()
    # Check if dominant text is just login form
    if len(lower_text) < 350 and _JUNK_RE.search(lower_text):
        return True

    # Reject Table of Contents header chunks
    if lower_text.startswith("table of contents") or lower_text.startswith("contents") or lower_text.startswith("index of schemes"):
        return True

    # Reject dot leader chunks (e.g. "... ... ... 12") common in PDF table-of-contents
    dot_count = text.count(".")
    if dot_count > 12 and (dot_count / len(text)) > 0.06:
        return True
    if len(re.findall(r"\.{4,}", text)) >= 2:
        return True

    return False


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


def remove_duplicate_lines(text: str, keep_short_lines: bool = True) -> str:
    """Remove exact duplicate lines (e.g. repeated boilerplate), but never
    collapse short lines that could legitimately repeat (e.g. a date or a
    fee amount listed in both a table and a summary) -- those are left
    alone by default."""
    lines = text.split("\n")
    seen = set()
    out: List[str] = []
    for line in lines:
        key = line.strip().lower()
        if not key:
            out.append(line)
            continue
        if keep_short_lines and len(key) < 25:
            out.append(line)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


def remove_repeated_header_footer(page_texts: List[str]) -> List[str]:
    """For multi-page PDFs, detect lines that repeat on (almost) every page
    -- typically headers/footers -- and strip them, leaving body text.

    Boilerplate is matched after normalizing digits (e.g. "Page 1 of 3"
    and "Page 2 of 3" are recognized as the same repeating pattern even
    though the literal page number changes), since exact-string matching
    alone would miss the very common "Page N of M" footer case."""
    if len(page_texts) < 3:
        return page_texts

    def norm_key(line: str) -> str:
        return re.sub(r"\d+", "#", line)

    line_page_counts = Counter()
    per_page_lines = []
    for pt in page_texts:
        lines = [l.strip() for l in pt.split("\n") if l.strip()]
        per_page_lines.append(lines)
        for l in {norm_key(x) for x in lines}:
            line_page_counts[l] += 1

    threshold = max(3, int(len(page_texts) * 0.6))
    boilerplate_keys = {k for k, c in line_page_counts.items() if c >= threshold and len(k) < 120}

    cleaned_pages = []
    for lines in per_page_lines:
        cleaned_pages.append("\n".join(l for l in lines if norm_key(l) not in boilerplate_keys))
    return cleaned_pages


def clean_text(text: str) -> str:
    text = normalize_encoding(text)
    text = normalize_whitespace(text)
    text = remove_duplicate_lines(text)
    return text


def clean_pdf_pages(page_texts: List[str]) -> List[str]:
    page_texts = remove_repeated_header_footer(page_texts)
    return [clean_text(p) for p in page_texts]
