import os
import sys
import re

backend_path = os.path.abspath(r"msmeassist-module1\backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app.unified_main import app
from app.core.rag_bridge import inprocess_search, inprocess_rag_query, get_inprocess_query_service

qs = get_inprocess_query_service()
retriever = qs.retriever

queries = [
    "How can I recover delayed payments from a buyer?",
    "Are there any export promotion schemes or subsidies for MSMEs?",
    "What is the subsidy percentage for ZED certification for micro enterprises?",
    "Can a registered MSME get loans without collateral under CGTMSE?",
    "What is the tax rate on cryptocurrency in India?",
    "What documents do I need for Udyam registration?",
]

print("=== RUNNING TEST QUERIES ===")
for q in queries:
    hits = retriever.search(q, top_k=3)
    print(f"\nQUERY: {q}")
    if not hits:
        print("  NO HITS RETURNED (Correctly refused or no matches)")
    else:
        for idx, h in enumerate(hits, 1):
            title = h.title or "Untitled"
            org = h.source_organization or "Unknown"
            snippet = h.text.replace("\n", " ")[:120].strip()
            print(f"  [{idx}] Score: {h.similarity_score:.3f} | Title: {title} | Org: {org}")
            print(f"      Text: {snippet}...")
