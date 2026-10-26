"""
PDF extraction for government PDF documents.

Preserves per-page text so retrieved chunks stay traceable to a page
number (required by the provenance layer).

Uses PyMuPDF (fitz) when available (per the spec's recommended stack);
falls back to pypdf, which is what's actually installed in this sandbox.
Both are hidden behind the same function signature so the rest of the
pipeline never has to know which backend produced the text.
"""
import io
from typing import Optional

from app.models.entities import ExtractedContent

try:
    import fitz  # PyMuPDF
    _BACKEND = "pymupdf"
except ImportError:
    fitz = None
    _BACKEND = "pypdf"
    from pypdf import PdfReader


def extract_pdf(raw_bytes: bytes, title_hint: Optional[str] = None) -> ExtractedContent:
    if _BACKEND == "pymupdf":
        return _extract_with_pymupdf(raw_bytes, title_hint)
    return _extract_with_pypdf(raw_bytes, title_hint)


def _extract_with_pymupdf(raw_bytes: bytes, title_hint: Optional[str]) -> ExtractedContent:
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    page_texts = [page.get_text("text") for page in doc]
    metadata = {k: v for k, v in (doc.metadata or {}).items() if v}
    title = metadata.get("title") or title_hint
    doc.close()
    full_text = "\n".join(page_texts).strip()
    return ExtractedContent(
        title=title,
        text=full_text,
        page_texts=page_texts,
        metadata=metadata,
    )


def _extract_with_pypdf(raw_bytes: bytes, title_hint: Optional[str]) -> ExtractedContent:
    reader = PdfReader(io.BytesIO(raw_bytes))
    page_texts = []
    for page in reader.pages:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:
            page_texts.append("")
    metadata = {}
    if reader.metadata:
        for k, v in reader.metadata.items():
            key = k.lstrip("/").lower()
            if v:
                metadata[key] = str(v)
    title = metadata.get("title") or title_hint
    full_text = "\n".join(page_texts).strip()
    return ExtractedContent(
        title=title,
        text=full_text,
        page_texts=page_texts,
        metadata=metadata,
    )
