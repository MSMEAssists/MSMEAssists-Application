"""
Master Recommendation Orchestrator for Module 3.

Coordinates:
  1. Profile ingestion from Module 1
  2. Scheme candidates from RAG System
  3. Pairwise LLM / analytical comparisons
  4. Bradley-Terry-Luce (BTL) Model fitting via MLE
  5. Explainable AI (XAI) feature attribution & ranking synthesis
"""
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.core.config import get_settings
from app.models.schemas import (
    CandidateScheme,
    PairwiseComparison,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.btl_engine import BtlMleSolver
from app.services.explainability import ExplainabilityEngine
from app.services.module1_client import Module1Client
from app.services.pairwise_evaluator import PairwiseEvaluator
from app.services.rag_client import RagClient

logger = logging.getLogger(__name__)

# User-isolated TTL cache for recommendations: cache_key -> (timestamp, RecommendationResponse)
_REC_CACHE: Dict[str, Tuple[float, RecommendationResponse]] = {}
_REC_CACHE_TTL = 300.0


class RecommendationService:
    def __init__(
        self,
        module1_client: Optional[Module1Client] = None,
        rag_client: Optional[RagClient] = None,
        pairwise_evaluator: Optional[PairwiseEvaluator] = None,
        btl_solver: Optional[BtlMleSolver] = None,
        explainability_engine: Optional[ExplainabilityEngine] = None,
    ):
        self.settings = get_settings()
        self.module1_client = module1_client or Module1Client()
        self.rag_client = rag_client or RagClient()
        self.pairwise_evaluator = pairwise_evaluator or PairwiseEvaluator()
        self.btl_solver = btl_solver or BtlMleSolver(
            max_iterations=self.settings.btl_max_iterations,
            tolerance=self.settings.btl_tolerance,
            smoothing=self.settings.btl_smoothing,
        )
        self.explainability_engine = explainability_engine or ExplainabilityEngine()

    async def generate_recommendations(
        self,
        request: RecommendationRequest,
        auth_token: Optional[str] = None,
    ) -> RecommendationResponse:
        """
        Executes the complete Explainable AI recommendation workflow.
        """
        # 1. Resolve MSME Profile
        profile = request.profile
        if not profile and auth_token:
            profile = await self.module1_client.get_profile(auth_token)

        # Fallback profile if none exists or unauthenticated
        if not profile:
            profile = {
                "business": {"name": "Your Enterprise", "type": "manufacturing", "industry": "General Engineering"},
                "financial": {"annual_turnover_inr": 4500000, "investment_inr": 1500000, "msme_classification": "micro"},
                "characteristics": {"is_women_owned": True, "social_category": "general", "is_rural_enterprise": True},
                "location": {"state": "Karnataka", "district": "Bengaluru Rural", "area_type": "rural"},
            }

        biz = profile.get("business", {})
        fin = profile.get("financial", {})
        business_name = biz.get("name", "Your Enterprise")
        msme_class = (fin.get("msme_classification") or "micro").capitalize()

        # 2. Resolve Location and Formulate Query
        target_location = (request.state or profile.get("location", {}).get("state") or "India").strip()
        filter_scope = (request.scope or "all").strip().lower()
        top_k = request.top_k or self.settings.top_k_candidates

        # Check in-memory cache
        cache_key = f"{business_name}_{msme_class}_{target_location}_{filter_scope}_{top_k}_{request.custom_query or ''}"
        now = time.time()
        if cache_key in _REC_CACHE:
            ts, cached_rec = _REC_CACHE[cache_key]
            if now - ts < _REC_CACHE_TTL:
                logger.info("Serving recommendation response from cache for key: %s", cache_key)
                return cached_rec

        search_query = request.custom_query or (
            f"Government subsidy scheme loans for {msme_class} {biz.get('type', 'manufacturing')} enterprise "
            f"{'women entrepreneur ' if profile.get('characteristics', {}).get('is_women_owned') else ''}"
            f"in {target_location}"
        )

        raw_candidates: List[CandidateScheme] = await self.rag_client.fetch_candidates(search_query, top_k=top_k * 2)

        # 3. Strict State vs Central Scope Detection & Disqualification
        REGIONAL_SCOPES = {
            "telangana": ["telangana", "hyderabad", "ts-ipass"],
            "karnataka": ["karnataka", "bengaluru", "bangalore"],
            "maharashtra": ["maharashtra", "mumbai", "pune"],
            "tamil nadu": ["tamil nadu", "tamilnadu", "chennai"],
            "gujarat": ["gujarat", "ahmedabad"],
            "andhra pradesh": ["andhra pradesh", "andhra", "amaravati"],
            "uttar pradesh": ["uttar pradesh", "lucknow"],
            "rajasthan": ["rajasthan", "jaipur"],
            "kerala": ["kerala", "cochin", "thiruvananthapuram"],
            "delhi": ["delhi"],
            "punjab": ["punjab"],
            "haryana": ["haryana"],
            "west bengal": ["west bengal", "kolkata"],
            "bihar": ["bihar", "patna"],
            "odisha": ["odisha", "orissa", "bhubaneswar"],
            "ner": ["ner", "north eastern", "sikkim", "assam", "tripura", "manipur", "meghalaya", "mizoram", "nagaland", "arunachal pradesh"],
        }

        user_loc_clean = target_location.lower()
        candidates: List[CandidateScheme] = []
        disqualified_other_states = 0

        for cand in raw_candidates:
            text_corpus = f"{cand.title} {cand.snippet} {cand.official_url} {cand.organization}".lower()
            detected_state = None
            import re
            for region_key, aliases in REGIONAL_SCOPES.items():
                if any(re.search(r"\b" + re.escape(alias) + r"\b", text_corpus) for alias in aliases):
                    detected_state = region_key
                    break

            if detected_state:
                cand.scheme_scope = "STATE"
                cand.state_jurisdiction = detected_state.title()
                # Check if it matches target state
                matches_user = False
                if user_loc_clean:
                    if user_loc_clean == detected_state:
                        matches_user = True
                    elif detected_state == "ner" and any(alias in user_loc_clean for alias in REGIONAL_SCOPES["ner"]):
                        matches_user = True
                    elif detected_state in REGIONAL_SCOPES and any(alias in user_loc_clean for alias in REGIONAL_SCOPES[detected_state]):
                        matches_user = True

                if not matches_user and user_loc_clean not in ("india", "all", "national", ""):
                    # STRICT DISQUALIFICATION: Discard schemes of other states
                    disqualified_other_states += 1
                    continue
            else:
                cand.scheme_scope = "CENTRAL"
                cand.state_jurisdiction = "All India"

            # Apply scope filter
            if filter_scope == "state" and cand.scheme_scope != "STATE":
                continue
            if filter_scope == "central" and cand.scheme_scope != "CENTRAL":
                continue

            candidates.append(cand)
            if len(candidates) >= top_k:
                break

        K = len(candidates)
        if K == 0:
            raise ValueError(f"No candidate schemes found matching location '{target_location}' and scope '{filter_scope}'.")

        # 4. Generate all pairwise comparisons K*(K-1)/2 concurrently with bounded concurrency
        pairwise_tasks = []
        pair_indices = []
        sem = asyncio.Semaphore(8)

        async def _eval_pair_bounded(sa: CandidateScheme, sb: CandidateScheme):
            async with sem:
                return await self.pairwise_evaluator.evaluate_pair(sa, sb, profile)

        for i in range(K):
            for j in range(i + 1, K):
                pairwise_tasks.append(_eval_pair_bounded(candidates[i], candidates[j]))
                pair_indices.append((i, j))

        raw_comparisons = await asyncio.gather(*pairwise_tasks)
        pairwise_results: List[PairwiseComparison] = []
        W = np.zeros((K, K), dtype=np.float64)

        for (i, j), comparison in zip(pair_indices, raw_comparisons):
            pairwise_results.append(comparison)
            prob_a = comparison.preference_probability
            prob_b = 1.0 - prob_a
            W[i, j] = prob_a
            W[j, i] = prob_b

        # 5. Fit Bradley-Terry-Luce Model via Maximum Likelihood Estimation (MM Algorithm)
        candidate_ids = [c.id for c in candidates]
        thetas, probs, iterations, converged, log_lik = self.btl_solver.fit(candidate_ids, W)

        # 6. Synthesize Explainable AI outputs
        pairwise_matrix, scheme_order = self.explainability_engine.build_pairwise_matrix(
            candidates, pairwise_results
        )
        feature_attributions = self.explainability_engine.compute_feature_attributions(pairwise_results)
        rankings = self.explainability_engine.assemble_rankings(
            candidates, thetas, probs, pairwise_matrix, pairwise_results, feature_attributions
        )

        state_schemes = [r for r in rankings if r.scheme_scope == "STATE"]
        central_schemes = [r for r in rankings if r.scheme_scope == "CENTRAL"]

        response = RecommendationResponse(
            business_name=business_name,
            msme_classification=msme_class,
            detected_location=target_location,
            filter_applied={"state": target_location, "scope": filter_scope},
            total_candidates=K,
            disqualified_other_states_count=disqualified_other_states,
            pairwise_comparisons_count=len(pairwise_results),
            btl_iterations=iterations,
            btl_log_likelihood=round(log_lik, 4),
            rankings=rankings,
            state_schemes=state_schemes,
            central_schemes=central_schemes,
            pairwise_matrix=pairwise_matrix,
            scheme_ids_order=scheme_order,
            pairwise_details=pairwise_results,
            feature_importance_summary=feature_attributions,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        _REC_CACHE[cache_key] = (now, response)
        if len(_REC_CACHE) > 200:
            oldest_key = min(_REC_CACHE.keys(), key=lambda k: _REC_CACHE[k][0])
            _REC_CACHE.pop(oldest_key, None)

        return response
