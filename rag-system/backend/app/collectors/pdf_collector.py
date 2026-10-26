"""
PDF collector: validates and fetches a specific, already-known PDF URL
(e.g. one discovered by html_collector during crawling, or added directly
via the admin API). Shares the same validation gate as html_collector --
no PDF is ever fetched without first passing app.core.url_validator.
"""
from typing import List, Optional

from app.core.source_registry import ApprovedSource
from app.core.url_validator import validate_url
from app.models.entities import RawFetchResult
from app.utils.http import fetch


def collect_pdf(
    url: str,
    approved_sources: List[ApprovedSource],
    resolve_dns: bool = True,
) -> Optional[RawFetchResult]:
    validation = validate_url(url, approved_sources, resolve_dns=resolve_dns)
    if not validation.is_valid:
        return None
    return fetch(validation.normalized_url)
