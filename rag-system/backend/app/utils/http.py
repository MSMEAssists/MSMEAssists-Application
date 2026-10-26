"""
Thin HTTP fetch wrapper. Every call must go through a pre-validated URL
(see app.core.url_validator) -- this module does not itself validate,
by design, so validation can't accidentally be bypassed for one call site
and not another; collectors are responsible for validating before calling.
"""
from typing import Optional

import requests

from app.core.config import settings
from app.models.entities import ContentFormat, RawFetchResult, now_ts


def fetch(url: str) -> RawFetchResult:
    headers = {"User-Agent": settings.user_agent}
    resp = requests.get(
        url, headers=headers, timeout=settings.request_timeout_seconds, allow_redirects=True
    )
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        content_format = ContentFormat.PDF
    else:
        content_format = ContentFormat.HTML

    return RawFetchResult(
        url=url,
        final_url=resp.url,
        status_code=resp.status_code,
        content_format=content_format,
        raw_bytes=resp.content,
        fetched_at=now_ts(),
        headers=dict(resp.headers),
    )
