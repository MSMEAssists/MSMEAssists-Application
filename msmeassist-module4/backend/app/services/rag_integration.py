"""
RAG System Integration Service for Module 4: Finance & Loan Agent.

Retrieves official loan schemes, government credit programs, eligibility details,
interest rate rules, tenure limits, and required documents from the existing RAG knowledge base.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_finance_settings

logger = logging.getLogger(__name__)


# Standard curated official loan/financing schemes for fallbacks
OFFICIAL_FINANCIAL_SCHEMES = [
    {
        "chunk_id": "cgtmse_1",
        "document_id": "doc_cgtmse",
        "title": "Credit Guarantee Fund Trust for Micro and Small Enterprises (CGTMSE)",
        "source_organization": "Ministry of MSME & SIDBI",
        "official_url": "https://www.cgtmse.in/",
        "knowledge_type": "LOAN",
        "text": "CGTMSE provides collateral-free credit facilities to micro and small enterprises with guarantee coverage up to ₹5 Crore (₹500 Lakhs). Women entrepreneurs and Micro units receive up to 85% guarantee cover with low guarantee fee structures.",
    },
    {
        "chunk_id": "pmegp_1",
        "document_id": "doc_pmegp",
        "title": "Prime Minister Employment Generation Programme (PMEGP)",
        "source_organization": "Ministry of MSME / KVIC",
        "official_url": "https://msme.gov.in/pmegp",
        "knowledge_type": "SUBSIDY",
        "text": "Credit-linked capital subsidy scheme providing 15% to 35% margin money subsidy on project costs up to ₹50 Lakh for manufacturing and ₹20 Lakh for service enterprises.",
    },
    {
        "chunk_id": "mudra_1",
        "document_id": "doc_mudra",
        "title": "Pradhan Mantri MUDRA Yojana (PMMY) — Kishore & Tarun",
        "source_organization": "Department of Financial Services / MUDRA",
        "official_url": "https://www.mudra.org.in/",
        "knowledge_type": "LOAN",
        "text": "Provides collateral-free working capital and capital expenditure loans up to ₹10-20 Lakhs for micro and small non-corporate enterprises across Kishore and Tarun categories.",
    },
    {
        "chunk_id": "sidbi_equipment_1",
        "document_id": "doc_sidbi",
        "title": "SIDBI Term Loan Scheme for Machinery and Equipment Purchase",
        "source_organization": "Small Industries Development Bank of India (SIDBI)",
        "official_url": "https://www.sidbi.in/",
        "knowledge_type": "LOAN",
        "text": "Direct term loan assistance for MSMEs to purchase modern machinery, technology upgrades, and solar/green energy equipment with attractive interest rates and flexible 5-7 year repayment tenure.",
    },
    {
        "chunk_id": "standup_1",
        "document_id": "doc_standup",
        "title": "Stand-Up India Scheme for Greenfield MSMEs",
        "source_organization": "Department of Financial Services / SIDBI",
        "official_url": "https://www.standupmitra.in/",
        "knowledge_type": "LOAN",
        "text": "Composite bank loans (term loan and working capital) between ₹10 Lakh and ₹1 Crore for setting up new greenfield enterprises by SC, ST, or Women entrepreneurs.",
    },
]


class RagIntegrationService:
    def __init__(self):
        self.settings = get_finance_settings()

    async def retrieve_loan_schemes(
        self,
        query: str,
        top_k: int = 5,
        knowledge_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves loan and financial schemes using the existing RAG pipeline.
        Tries in-memory execution first, then HTTP call to /api/retrieval/search, and falls back to curated corpus.
        """
        # 1. Try internal in-memory retrieval if running inside unified FastAPI app
        try:
            from app.api.deps import get_query_service
            query_service = get_query_service()
            results = query_service.retriever.search(
                query=query,
                top_k=top_k,
                knowledge_type=knowledge_type,
            )
            if results and len(results) > 0:
                return [r.__dict__ for r in results]
        except Exception:
            pass  # Fall through to HTTP or fallback

        # 2. Try HTTP call to RAG server URL
        url = f"{self.settings.rag_service_url.rstrip('/')}/api/retrieval/search"
        payload = {"query": query, "top_k": top_k}
        if knowledge_type:
            payload["knowledge_type"] = knowledge_type

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data
        except Exception as e:
            logger.info(f"RAG HTTP call to {url} failed ({e}); using official fallback scheme corpus.")

        # 3. Fallback to curated official financial schemes
        results = []
        q_words = set(query.lower().split())
        for scheme in OFFICIAL_FINANCIAL_SCHEMES:
            score = 0.5
            text_lower = scheme["text"].lower() + " " + scheme["title"].lower()
            for w in q_words:
                if len(w) > 3 and w in text_lower:
                    score += 0.1
            res_dict = dict(scheme)
            res_dict["similarity_score"] = min(score, 0.95)
            results.append(res_dict)

        results.sort(key=lambda x: -x.get("similarity_score", 0.0))
        return results[:top_k]
