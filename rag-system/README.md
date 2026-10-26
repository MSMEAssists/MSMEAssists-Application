# Standalone Government Information RAG System

A retrieval-augmented Q&A system that ingests information **exclusively**
from approved official Indian government websites and answers questions
with mandatory source-URL provenance on every result.

This is a fully standalone project: **no dependency on MSMEAssist Module
1–5**, no user profiles, no recommendation ranking, no BTL/MLE, no
personalized scheme recommendations. See `docs/architecture.md` for the
full design.

## Quick links

- `backend/README.md` — setup, running, configuration
- `docs/architecture.md` — module map and design decisions
- `docs/ingestion.md`, `docs/retrieval.md`, `docs/rag.md`, `docs/sources.md`
- `backend/tests/` — automated test suite (50 tests)
- `backend/verify_pipeline.py` — runnable end-to-end verification script

---

## Final Verification Report

**Architecture implemented:** Dual-pipeline RAG exactly as specified —
Pipeline 1 (Knowledge Ingestion: source validation → discovery → URL
validation → fetch → HTML/PDF extraction → cleaning → normalization →
deduplication → versioning → knowledge classification → chunking →
embedding → vector database) and Pipeline 2 (Query/Retrieval: query
processing → query embedding → vector search → metadata filtering →
similarity filtering → top-K → provenance resolution → RAG answer
generation).

**Official sources configured:** 7 (Ministry of MSME, DGFT, GST Portal,
SIDBI, MCA, Department of Expenditure, Government e-Procurement) — see
`docs/sources.md`.

**Automated test suite: 50/50 passing** (`python -m unittest discover -s
backend/tests`, or `pytest backend/tests`), covering:
- URL validation & SSRF protection (approved-domain acceptance,
  unapproved-domain rejection, disallowed protocols, localhost/private-IP/
  cloud-metadata rejection, malformed URLs, disabled-source rejection)
- HTML extraction (nav/script stripping, heading/list/table preservation,
  key-content preservation)
- PDF extraction (page-number preservation, repeated header/footer removal)
- Cleaning/normalization (whitespace, dedup, no-loss-of-meaning checks)
- Deduplication & versioning (new / unchanged / new-version decisions)
- Classification (SCHEME vs LOAN vs 10 other types; **no invented
  fields** — verified by an explicit test asserting no fabricated interest
  rate)
- Chunking (size/overlap, page-number-aware for PDFs)
- Embeddings & vector store (dimension correctness, semantic ranking,
  metadata filtering, persist/load round-trip, upsert-replaces-not-
  duplicates)
- **Full pipeline integration** (real fixture ingestion → real chunking →
  real embedding → real retrieval → real RAG answer, including a
  **no-hallucination test**: an off-topic query correctly returns "I could
  not find sufficient information..." with zero citations, never an
  invented answer)

Run the human-readable version of this yourself:
```bash
cd backend && python verify_pipeline.py
```

### Numbers from the fixture-based verification run

| Metric | Value |
|---|---|
| Documents collected | 3 (1 scheme page, 1 loan page, 1 procurement PDF) |
| Scheme records | 1 |
| Loan/credit records | 1 |
| Chunks generated | 7 |
| Embedding status | OK (offline TF-IDF+SVD, 64 dims) |
| Vector store status | OK (numpy backend, 7 vectors indexed) |
| PDF page references | Preserved (pages 1–3 all traceable) |
| Provenance verification | PASS — every document has ≥1 provenance record carrying its official URL |
| Loan-query retrieval | PASS — correctly returns the LOAN document as top result |
| No-hallucination test | PASS — off-topic query correctly refused, zero citations |

### Known limitations / what was NOT verified here

This code was authored and tested in a sandboxed environment with **no
internet access** and without `fastapi`, `pydantic`, `faiss`, or `pymongo`
pre-installed (only Python stdlib + numpy/scikit-learn/BeautifulSoup/
requests/pypdf were available, and nothing could be pip-installed). As a
result:

1. **Live ingestion against the real approved `.gov.in` sites has not been
   executed or verified.** The collector/validator code path is real and
   unit-tested against the validation logic, but the actual network fetch
   from msme.gov.in, dgft.gov.in, etc. needs to be run in an environment
   with internet access. Do this before relying on the system: `pip
   install -r backend/requirements.txt` then `POST /api/ingestion/run`.
2. **The FastAPI/pydantic API layer (`app/api/`, `app/main.py`,
   `app/schemas/`) has not been executed** in this environment (package
   not installed) — it has been syntax-checked and code-reviewed, but not
   run under `uvicorn` or hit with real HTTP requests. Install
   dependencies and smoke-test the endpoints before production use.
3. **FAISS and MongoDB backends are implemented but not exercised** here
   (packages not installed) — the numpy vector store and sqlite metadata
   DB were used for all verification instead, since they implement the
   identical interfaces with zero install requirements.
4. **The default embedding provider (`tfidf_svd`) is lexical, not deep
   semantic.** It's sufficient to pass the hallucination-refusal test and
   rank clearly on-topic queries correctly, but on a tiny 3-document
   fixture corpus, broad/generic queries can occasionally rank a
   topically-adjacent document above the ideal one (documented directly in
   `verify_pipeline.py`'s own output). For production-quality semantic
   retrieval, install `sentence-transformers` and set
   `EMBEDDING_PROVIDER=sentence_transformers`.
5. **No mock RAG was used anywhere** in the tested pipeline — every
   retrieval result and every RAG answer in the test suite is produced by
   the real extraction → chunking → embedding → vector-search chain
   running against real (fixture) content. The only simulated step is the
   network fetch itself (`RawFetchResult` is constructed from local fixture
   bytes in tests, documented explicitly in
   `backend/tests/test_pipeline_integration.py`'s module docstring),
   because this environment cannot reach the internet.

### Remaining issues / suggested next steps

- Run live ingestion once deployed with internet access; review the first
  batch of classified SCHEME/LOAN records for accuracy before trusting
  them at scale (the classifier is intentionally conservative but is
  rule-based, not ML-based).
- Wire a real `LLMClient` (see `docs/rag.md`) for natural-language answer
  generation — the current fallback is a safe, citation-accurate but
  purely extractive answer.
- Consider `sentence_transformers` + `faiss` for production retrieval
  quality/scale once those packages are available in your deployment
  environment.
- Extend structured field extraction (currently SCHEME/LOAN) to the other
  9 knowledge types as needed.

---

*Per the original scope: this is ONLY the standalone RAG system. No
MSMEAssist module connections, no recommendation ranking, no BTL, no MLE
were implemented.*
