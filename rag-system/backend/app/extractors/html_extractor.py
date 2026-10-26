"""
HTML extraction for government web pages.

Extracts title, headings, paragraphs, lists, tables, meaningful links and
basic metadata, while stripping navigation/scripts/styles/ads/other noise.
"""
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment

from app.models.entities import ExtractedContent

NOISE_TAGS = [
    "script", "style", "noscript", "svg", "iframe", "form",
    "nav", "header", "footer", "aside",
]

NOISE_CLASS_ID_HINTS = [
    "nav", "navbar", "menu", "footer", "header", "breadcrumb",
    "advert", "advertisement", "ads", "cookie", "banner", "social-share",
    "sidebar", "skip-link", "back-to-top",
]


def _is_noise(tag) -> bool:
    if not getattr(tag, "attrs", None):
        return False
    identifiers = " ".join(
        [tag.get("id", "") or ""] + (tag.get("class", []) or [])
    ).lower()
    return any(hint in identifiers for hint in NOISE_CLASS_ID_HINTS)


def extract_html(html: str, base_url: str) -> ExtractedContent:
    soup = BeautifulSoup(html, "html.parser")

    # Remove obvious noise
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    for tag in soup.find_all(True):
        if _is_noise(tag):
            tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else None

    headings: List[str] = []
    for level in ["h1", "h2", "h3", "h4"]:
        for h in soup.find_all(level):
            text = h.get_text(" ", strip=True)
            if text:
                headings.append(text)

    paragraphs: List[str] = []
    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)

    lists: List[List[str]] = []
    for l in soup.find_all(["ul", "ol"]):
        items = [li.get_text(" ", strip=True) for li in l.find_all("li", recursive=False)]
        items = [i for i in items if i]
        if items:
            lists.append(items)

    tables: List[List[List[str]]] = []
    for table_tag in soup.find_all("table"):
        rows = []
        for tr in table_tag.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)

    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        links.append(urljoin(base_url, href))

    metadata = {}
    for meta in soup.find_all("meta"):
        name = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if name and content:
            metadata[name.lower()] = content

    # Build full_text by walking the document in original order (not by
    # clustering all headings, then all paragraphs, etc.) -- section-based
    # field extraction downstream depends on a heading being immediately
    # followed by its own body text, the way it actually reads on the page.
    ordered_lines: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if tag.name == "li" and tag.find_parent("li"):
            continue  # avoid duplicating nested list items
        ordered_lines.append(text)

    full_text = "\n".join(ordered_lines).strip()
    if not full_text:
        # fallback: whole visible text
        full_text = soup.get_text("\n", strip=True)

    return ExtractedContent(
        title=title,
        text=full_text,
        headings=headings,
        lists=lists,
        tables=tables,
        links=sorted(set(links)),
        page_texts=None,
        metadata=metadata,
    )
