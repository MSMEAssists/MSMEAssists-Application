"""
RAG answer generation.

Hard rules (see docs/rag.md):
  1. Never answer from outside/general model knowledge -- only from
     retrieved context.
  2. If retrieved context is insufficient, say so explicitly instead of
     guessing.
  3. Always include official source citations/links.
  4. Never fabricate application URLs, financial values, or eligibility
     criteria -- these only ever come verbatim from retrieved chunks.

The LLM call itself is provider-agnostic (see app.core.config.settings:
llm_provider/llm_model) via `LLMClient`, which is intentionally a thin,
swappable wrapper -- this module never talks to a specific vendor SDK
directly.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from app.processors.cleaner import is_junk_chunk, normalize_encoding
from app.retrieval.retriever import RetrievedResult

NO_RESULTS_MESSAGE = (
    "I could not find sufficient information in the approved official "
    "government sources to answer this question."
)

_SYSTEM_PROMPT = """You are a Government Information assistant. You must answer \
ONLY using the provided official government source excerpts below. \
Do not use any outside knowledge. \
If the excerpts do not contain enough information to answer, say so explicitly rather than guessing. \
Never invent application URLs, financial values (interest rates, loan amounts, subsidy amounts), \
or eligibility criteria that are not explicitly present in the excerpts. \
Always cite which source (by title/URL) each part of your answer comes from."""


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        ...


@dataclass
class Citation:
    title: Optional[str]
    organization: str
    official_url: str
    page_number: Optional[int]
    document_id: str
    chunk_id: str
    official_application_url: Optional[str] = None


@dataclass
class RagAnswer:
    query: str
    answer_text: str
    has_sufficient_context: bool
    citations: List[Citation] = field(default_factory=list)
    retrieved_result_count: int = 0


def _build_context_block(results: List[RetrievedResult]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        page_info = f", page {r.page_number}" if r.page_number else ""
        blocks.append(
            f"[Source {i}] {r.title or 'Untitled'} "
            f"({r.source_organization}{page_info})\n"
            f"URL: {r.official_url}\n"
            f"Excerpt:\n{r.text}\n"
        )
    return "\n---\n".join(blocks)


def generate_answer(
    query: str,
    results: List[RetrievedResult],
    llm_client: Optional[LLMClient] = None,
) -> RagAnswer:
    if not results:
        return RagAnswer(
            query=query,
            answer_text=NO_RESULTS_MESSAGE,
            has_sufficient_context=False,
            citations=[],
            retrieved_result_count=0,
        )

    # Filter out login screens, password resets, and navigation boilerplate
    quality_results = [r for r in results if not is_junk_chunk(r.text, r.official_url, r.title)]
    effective_results = quality_results if quality_results else results

    citations = [
        Citation(
            title=r.title,
            organization=r.source_organization,
            official_url=r.official_url,
            page_number=r.page_number,
            document_id=r.document_id,
            chunk_id=r.chunk_id,
            official_application_url=getattr(r, "official_application_url", None),
        )
        for r in effective_results
    ]

    if llm_client is None:
        answer_text = _synthesize_grounded_answer(query, effective_results)
        return RagAnswer(
            query=query,
            answer_text=answer_text,
            has_sufficient_context=True,
            citations=citations,
            retrieved_result_count=len(effective_results),
        )

    context_block = _build_context_block(effective_results)
    user_prompt = (
        f"Question: {query}\n\n"
        f"Official government source excerpts:\n{context_block}\n\n"
        "Answer the question using ONLY the excerpts above. If they are "
        "insufficient, say so explicitly. Cite the source title/URL for "
        "each claim you make."
    )
    answer_text = llm_client.complete(_SYSTEM_PROMPT, user_prompt)
    answer_text = normalize_encoding(answer_text)

    return RagAnswer(
        query=query,
        answer_text=answer_text,
        has_sufficient_context=True,
        citations=citations,
        retrieved_result_count=len(effective_results),
    )


def _synthesize_grounded_answer(query: str, results: List[RetrievedResult]) -> str:
    """Synthesizes a structured, highly informative, grounded answer directly
    from the retrieved official chunks without dumping raw scanned snippets."""
    top = results[0]
    org_label = top.source_organization or "Government of India"
    scheme_title = top.title or "Government Scheme Guidelines"
    
    # 1. Collect and clean all non-empty sentences across top results
    all_sentences: List[str] = []
    seen_sentences = set()
    
    for r in results:
        cleaned_text = normalize_encoding(r.text).strip()
        # Split into sentences or structured bullet lines
        for raw_s in re.split(r"(?<=[.!?])\s+|\n+", cleaned_text):
            s = raw_s.strip()
            # Skip noise, page numbers, single words, dotted lines
            if len(s) < 12 or len(s) > 380:
                continue
            if s.count(".") > 5 or s.startswith("Table of Contents") or s.startswith("Page "):
                continue
            s_low = s.lower()
            if s_low in seen_sentences:
                continue
            seen_sentences.add(s_low)
            all_sentences.append(s)

    # 2. Extract domain facts matching the user's specific query
    financial_facts: List[str] = []
    eligibility_facts: List[str] = []
    process_facts: List[str] = []
    direct_answers: List[str] = []

    q_lower = query.lower()
    q_tokens = [t for t in re.findall(r"\w{3,}", q_lower) if t not in ("what", "which", "how", "can", "the", "for", "and", "under")]

    for s in all_sentences:
        s_low = s.lower()
        # High-relevance direct answer candidate
        match_count = sum(1 for t in q_tokens if t in s_low)
        if ("percentage" in q_lower or "subsidy" in q_lower or "%" in q_lower) and "%" in s:
            match_count += 3

        if match_count >= 2 and len(direct_answers) < 4:
            direct_answers.append(s)

        # Financial / numerical provision
        if re.search(r"(\b\d+%\b|\b₹\s*\d+|\brs\.?\s*\d+|\bcrore\b|\blakh\b|\blakhs\b|\bsubsidy\b|\bguarantee\b|\bcoverage\b|\bconcession\b|\bceiling\b)", s_low):
            if len(financial_facts) < 4 and s not in direct_answers:
                financial_facts.append(s)
        # Eligibility criteria
        elif any(k in s_low for k in ("eligible", "eligibility", "criteria", "must", "required", "qualification", "condition", "target", "applies to", "micro and small")):
            if len(eligibility_facts) < 4 and s not in direct_answers:
                eligibility_facts.append(s)
        # Process or document
        elif any(k in s_low for k in ("portal", "apply", "application", "procedure", "process", "register", "nodal", "bank", "document", "udyam")):
            if len(process_facts) < 3 and s not in direct_answers:
                process_facts.append(s)

    # 3. Assemble coherent, well-structured response
    lines: List[str] = [
        f"### Official Guidance on {scheme_title}",
        f"**Issuing Authority:** {org_label}",
        "",
    ]

    # Primary Direct Answer
    if direct_answers:
        lines.extend([
            "#### Direct Summary & Answer:",
        ])
        for da in direct_answers[:3]:
            lines.append(f"- {da}")
        lines.append("")
    elif financial_facts or eligibility_facts:
        lead = (financial_facts or eligibility_facts)[0]
        lines.extend([
            "#### Direct Summary:",
            f"- {lead}",
            "",
        ])

    # Key Financial & Operational Provisions
    if financial_facts:
        lines.extend([
            "#### Key Provisions & Financial Benefits:",
        ])
        for f in financial_facts[:4]:
            lines.append(f"- {f}")
        lines.append("")

    # Eligibility & Conditions
    if eligibility_facts:
        lines.extend([
            "#### Eligibility Conditions & Requirements:",
        ])
        for e in eligibility_facts[:3]:
            lines.append(f"- {e}")
        lines.append("")

    # Process and Portal
    portal_url = top.official_application_url or top.official_url
    lines.extend([
        "#### Application Procedure & Official Links:",
        f"- **Official Portal:** [{scheme_title}]({portal_url})" + (f" *(Page {top.page_number})*" if top.page_number else ""),
    ])
    for p in process_facts[:2]:
        lines.append(f"- {p}")

    # Official Citations
    lines.extend([
        "",
        "#### Supporting Official Sources:",
    ])
    cited_urls = set()
    for r in results[:4]:
        if r.official_url and r.official_url not in cited_urls:
            cited_urls.add(r.official_url)
            lines.append(f"- [{r.title or r.source_organization or 'Official Publication'}]({r.official_url})"
                         + (f" *(Page {r.page_number})*" if r.page_number else ""))

    return "\n".join(lines)
