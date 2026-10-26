"""
Module 3 Integration Service for Module 4: Finance & Loan Agent.

Consumes pairwise BTL ranked scheme outputs from Module 3's Explainable AI
Recommendation Engine so Module 4 can perform financial suitability analysis.
"""
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import get_finance_settings

logger = logging.getLogger(__name__)


class Module3IntegrationService:
    def __init__(self):
        self.settings = get_finance_settings()

    async def get_ranked_recommendations(
        self,
        profile_dict: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Consumes ranked scheme outputs from Module 3.
        Uses in-memory service if inside unified server, or HTTP fallback.
        """
        # 1. Try internal in-memory call
        try:
            from app.services.recommendation_service import RecommendationService
            from app.models.schemas import RecommendationRequest

            rec_service = RecommendationService()
            request_obj = RecommendationRequest(profile=profile_dict, top_k=top_k)
            response = await rec_service.generate_recommendations(request_obj, auth_token=auth_token)

            if response and response.rankings:
                return [r.dict() for r in response.rankings]
        except Exception:
            pass  # Fall through to HTTP or fallback

        # 2. Try HTTP call
        url = f"{self.settings.module3_service_url.rstrip('/')}/api/recommendations/rank"
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token

        payload = {"profile": profile_dict, "top_k": top_k}

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    rankings = data.get("rankings", [])
                    if rankings:
                        return rankings
        except Exception as e:
            logger.info(f"Module 3 HTTP call to {url} failed ({e}); proceeding with direct RAG recommendations.")

        return []
