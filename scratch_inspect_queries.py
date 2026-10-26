import os
import sys
from pathlib import Path
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent / "msmeassist-module1" / "backend"
RAG_BACKEND = Path(__file__).resolve().parent / "rag-system" / "backend"

sys.path.insert(0, str(BACKEND_DIR))
os.environ["SQLITE_PATH"] = str(RAG_BACKEND / "data" / "gov_rag.db")
os.environ["VECTOR_STORE_PATH"] = str(RAG_BACKEND / "data" / "vector_store")
os.environ["SOURCE_DOCUMENTS_PATH"] = str(RAG_BACKEND / "data" / "source_documents")

from app.core import rag_bridge
qs = rag_bridge.get_inprocess_query_service()
retriever = qs.retriever
retriever._ensure_lexical_index()

queries = [
    "I need 15 lakh but cannot provide property as collateral. What are my options?",
    "What registrations and documents should I prepare before applying for a machinery loan?",
]

for q in queries:
    print(f"\n=======================================================")
    print(f"QUERY: {q}")
    print(f"=======================================================")
    
    # 1. Terms
    import re
    tokens = re.findall(r"\b[A-Za-z0-9&-]{2,}\b", q)
    print(f"Tokens in query: {tokens}")
    
    # 2. Check substantive terms extracted by retriever
    import sys
    retriever_mod = sys.modules[type(retriever).__module__]
    _GENERIC_QUERY_WORDS = retriever_mod._GENERIC_QUERY_WORDS
    acronyms = set()
    substantive = []
    for token in tokens:
        lower_token = token.lower()
        if lower_token in _GENERIC_QUERY_WORDS:
            continue
        if (token.isupper() or "-" in token) and lower_token not in ("msme", "in"):
            acronyms.add(lower_token)
        if len(lower_token) >= 3 and lower_token not in _GENERIC_QUERY_WORDS:
            substantive.append(lower_token)
    print(f"Acronyms: {acronyms}")
    print(f"Substantive terms: {substantive}")
    
    # 3. Dense search
    q_emb = retriever.embedding_service.embed([q]).vectors[0]
    hits = retriever.vector_store.search(q_emb, top_k=5)
    print("\nTop 5 Dense Hits:")
    for h in hits:
        c = retriever.repository.get_chunk(h.chunk_id)
        t = c.get("title") if c else "N/A"
        print(f"  dense={h.score:.4f} | cid={h.chunk_id} | title={t}")
        
    # 4. Lexical search
    q_vec = retriever._lexical_vectorizer.transform([q])
    sims = (q_vec @ retriever._lexical_matrix.T).toarray()[0]
    top_lex = np.argsort(sims)[::-1][:10]
    print("\nTop 10 Lexical Hits:")
    for idx in top_lex:
        c = retriever._lexical_chunks[idx]
        print(f"  lex={sims[idx]:.4f} | cid={c['chunk_id']} | title={c.get('title')}")
        print(f"    text snippet: {c.get('text', '')[:120]}...")

    # 5. Hybrid search final results
    results = retriever.search(q, top_k=5)
    print(f"\nFinal Hybrid Search Results ({len(results)} hits):")
    for r in results:
        print(f"  hybrid={r.similarity_score:.4f} | title={r.title} | doc_id={r.document_id} | chunk_id={r.chunk_id}")
