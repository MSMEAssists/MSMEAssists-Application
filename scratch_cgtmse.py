import sys
import os

backend_path = os.path.abspath(r"msmeassist-module1\backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.unified_main import app
from app.core.rag_bridge import inprocess_search, inprocess_rag_query

hits = inprocess_search("CGTMSE collateral-free loan credit guarantee", top_k=5)
print("Hits for 'CGTMSE collateral-free loan credit guarantee':")
for h in hits:
    print(f" - {h.get('similarity_score', 0):.3f} | {h.get('title')} | {h.get('official_url')}")
    print(f"   {h.get('text', '')[:100].replace(chr(10), ' ')}")
