"""
Configurable, section-aware chunking.

Splits text on section/paragraph boundaries first, then packs those units
into chunks up to `chunk_size` characters with `chunk_overlap` characters
of overlap between consecutive chunks -- so semantic boundaries are
respected where practical instead of chunking mid-sentence.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings

_SECTION_SPLIT_RE = re.compile(r"\n\s*\n")


@dataclass
class ChunkSpan:
    text: str
    section: Optional[str]
    page_number: Optional[int]


def _split_into_units(text: str) -> List[str]:
    units = [u.strip() for u in _SECTION_SPLIT_RE.split(text) if u.strip()]
    if not units:
        units = [text.strip()] if text.strip() else []
    return units


def _guess_section(unit: str) -> Optional[str]:
    first_line = unit.split("\n", 1)[0].strip()
    if 0 < len(first_line) <= 80 and not first_line.endswith((".", ",")):
        return first_line
    return None


def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    page_number: Optional[int] = None,
) -> List[ChunkSpan]:
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    units = _split_into_units(text)

    spans: List[ChunkSpan] = []
    buffer = ""
    buffer_section: Optional[str] = None

    def flush():
        nonlocal buffer, buffer_section
        if buffer.strip():
            spans.append(ChunkSpan(text=buffer.strip(), section=buffer_section, page_number=page_number))
        buffer = ""

    for unit in units:
        section_guess = _guess_section(unit)
        if not buffer:
            buffer_section = section_guess or buffer_section

        candidate = (buffer + "\n\n" + unit).strip() if buffer else unit

        if len(candidate) <= chunk_size:
            buffer = candidate
            continue

        # Current buffer is full; flush it, then start a new buffer that
        # carries `chunk_overlap` chars of tail context forward.
        if buffer:
            flush()
            overlap_tail = buffer[-chunk_overlap:] if chunk_overlap > 0 else ""
            buffer = (overlap_tail + "\n\n" + unit).strip() if overlap_tail else unit
            buffer_section = section_guess or buffer_section
        else:
            # Single unit longer than chunk_size: hard-split it.
            for start in range(0, len(unit), chunk_size - chunk_overlap):
                piece = unit[start:start + chunk_size]
                if piece.strip():
                    spans.append(ChunkSpan(text=piece.strip(), section=section_guess, page_number=page_number))
            buffer = ""
            buffer_section = None

        # If the new buffer itself already exceeds chunk_size (long unit
        # following overlap), flush again immediately.
        while len(buffer) > chunk_size:
            piece = buffer[:chunk_size]
            spans.append(ChunkSpan(text=piece.strip(), section=buffer_section, page_number=page_number))
            buffer = buffer[chunk_size - chunk_overlap:]

    flush()
    return spans


def chunk_document(
    text: str,
    page_texts: Optional[List[str]] = None,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[ChunkSpan]:
    """Chunk a whole document. If `page_texts` is provided (PDF), chunk each
    page independently so every chunk retains an accurate page number."""
    if page_texts:
        all_spans: List[ChunkSpan] = []
        for i, page_text in enumerate(page_texts, start=1):
            if not page_text or not page_text.strip():
                continue
            all_spans.extend(
                chunk_text(page_text, chunk_size, chunk_overlap, page_number=i)
            )
        return all_spans

    return chunk_text(text, chunk_size, chunk_overlap, page_number=None)
