# Government Information RAG — Backend

Standalone RAG system that ingests information **only** from approved
official Indian government websites and answers questions with mandatory
source-URL provenance. See `../docs/` for architecture, ingestion,
retrieval, RAG, and source-registry details.

## Quick start (environment with internet access)

```bash
cd backend
python -m venv venv && source venv/bin/activate  (windows: .\venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env

# Run the offline-safe pipeline test suite (no network required):
pytest tests/ -v

# Start the API:
uvicorn app.main:app --reload

# Trigger ingestion for one approved source:
curl -X POST http://localhost:8000/api/ingestion/run \
  -H "Content-Type: application/json" \
  -d '{"source_id": "msme", "max_pages": 20}'

# Ask a question:
curl -X POST http://localhost:8000/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What government schemes are available for MSMEs?"}'
```

## Zero-install core (this repo's default configuration)

Out of the box — no FAISS, no MongoDB, no sentence-transformers, no
internet required for the *logic* itself — using:

- `EMBEDDING_PROVIDER=tfidf_svd` (scikit-learn)
- `VECTOR_STORE_BACKEND=numpy`
- `DB_BACKEND=sqlite`

Run `python -m unittest discover -s tests` (or `pytest`) to exercise the
full pipeline against local fixtures without any network access. Live
ingestion against the real `.gov.in` domains still requires internet
access and `pip install -r requirements.txt` (specifically `requests`,
which is used regardless of backend choice, plus `fastapi`/`uvicorn` to
actually serve the API).

## Swapping in production-grade backends

| Component | Default | Production option | How |
|---|---|---|---|
| Embeddings | `tfidf_svd` | `sentence_transformers` | `pip install sentence-transformers`, set `EMBEDDING_PROVIDER=sentence_transformers`, `EMBEDDING_MODEL_NAME=<model>` |
| Vector store | `numpy` | `faiss` | `pip install faiss-cpu`, set `VECTOR_STORE_BACKEND=faiss` |
| Metadata DB | `sqlite` | `mongodb` | Implement `MongoRepository` against `app/db/repository.py`'s interface, set `DB_BACKEND=mongodb`, `MONGODB_URI=...` |
| Answer LLM | extractive fallback | any provider | Implement `LLMClient.complete()` (see `app/rag/answer_generator.py`) and wire it in `app/api/deps.py::get_query_service` |

## Project structure

```
backend/
├── app/
│   ├── api/            # FastAPI routes + dependency wiring
│   ├── collectors/      # HTML/PDF collection (validated fetch)
│   ├── core/            # config, source registry, URL/SSRF validation
│   ├── chunking/        # section-aware chunker
│   ├── db/               # sqlite metadata repository
│   ├── embeddings/       # embedding provider abstraction
│   ├── extractors/       # HTML/PDF content extraction
│   ├── models/           # domain dataclasses
│   ├── processors/       # cleaning, dedup, classification
│   ├── provenance/       # provenance record construction
│   ├── rag/              # answer generation
│   ├── retrieval/        # query -> retrieval pipeline
│   ├── schemas/          # pydantic API schemas
│   ├── services/         # ingestion + query orchestration
│   ├── utils/            # HTTP fetch wrapper
│   └── vectorstore/      # vector store abstraction (numpy/FAISS)
├── tests/
│   └── fixtures/         # local HTML/PDF fixtures used by automated tests
├── requirements.txt
└── .env.example
```

## Known limitations (see root README for the full verification report)

- Live ingestion against the real approved `.gov.in` domains has not been
  executed in the environment this code was authored in (no internet
  access there). Run it yourself once you have connectivity — the code
  path is real, not mocked.
- The default `tfidf_svd` embedding provider is a lexical (not deep
  semantic) method; it's accurate enough to pass genuinely-unrelated-query
  hallucination tests, but for best retrieval quality on production-scale
  content, switch to `sentence_transformers` or another dense embedding
  model.
