"""
Pairwise Evaluator for Scheme Comparison.

Given two candidate schemes and an MSME business profile, determines:
  - Which scheme is more suitable and advantageous
  - Preference probability (0.5 for tie, >0.5 if A wins, <0.5 if B wins)
  - Detailed comparative rationale
  - Driving profile attributes that tipped the scale
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.models.schemas import CandidateScheme, PairwiseComparison

logger = logging.getLogger(__name__)


class PairwiseEvaluator:
    """
    Compares pairs of candidate government schemes against an MSME profile.
    Uses LLM when configured, with an analytical rule-grounded fallback.
    """

    def __init__(self):
        self.settings = get_settings()

    async def evaluate_pair(
        self,
        scheme_a: CandidateScheme,
        scheme_b: CandidateScheme,
        profile: Dict[str, Any],
    ) -> PairwiseComparison:
        """Evaluates Scheme A vs Scheme B for the given MSME profile."""
        provider = self.settings.llm_provider

        # Attempt LLM comparison if configured
        if provider in ("gemini", "anthropic", "openai"):
            try:
                llm_result = await self._call_llm_pairwise(scheme_a, scheme_b, profile)
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning(f"LLM pairwise evaluation failed, falling back to analytical evaluator: {e}")

        # Default / Fallback: Analytical Grounded Evaluator
        return self._analytical_pairwise_evaluation(scheme_a, scheme_b, profile)

    def _analytical_pairwise_evaluation(
        self,
        scheme_a: CandidateScheme,
        scheme_b: CandidateScheme,
        profile: Dict[str, Any],
    ) -> PairwiseComparison:
        """
        Deterministic, rule-grounded pairwise evaluator based on multi-criteria utility:
          1. Enterprise classification fit (Micro / Small / Medium)
          2. Industry / Sector match (Manufacturing / Services / Trading)
          3. Special characteristic bonuses (Women-owned, SC/ST, Rural, Startup)
          4. Benefit intensity (Subsidies, credit guarantees, interest concessions)
          5. Procedural compliance barrier (Required documents friction)
        """
        biz = profile.get("business", {})
        fin = profile.get("financial", {})
        char = profile.get("characteristics", {})
        loc = profile.get("location", {})

        biz_name = biz.get("name", "Your Enterprise")
        biz_type = (biz.get("type") or "manufacturing").lower()
        msme_class = (fin.get("msme_classification") or "micro").lower()
        is_women = char.get("is_women_owned", False)
        social_cat = (char.get("social_category") or "general").lower()
        is_rural = char.get("is_rural_enterprise", False) or (loc.get("area_type") == "rural")
        is_startup = char.get("is_startup_recognized", False)

        def score_scheme(s: CandidateScheme) -> Tuple[float, List[str], List[str]]:
            score = 50.0  # baseline
            drivers = []
            reasons = []

            text_corpus = f"{s.title} {s.snippet} {' '.join(s.benefits)} {' '.join(s.eligibility_criteria)}".lower()

            # 1. Classification alignment
            if msme_class in text_corpus or "msme" in text_corpus or "micro" in text_corpus:
                score += 15.0
                drivers.append(f"msme_classification ({msme_class})")
                reasons.append(f"explicitly covers {msme_class} enterprises")

            # 2. Sector alignment
            if biz_type in text_corpus or "manufacturing" in text_corpus or "service" in text_corpus:
                score += 12.0
                drivers.append(f"sector ({biz_type})")
                reasons.append(f"tailored for {biz_type} activities")

            # 3. Inclusion & Special Category bonuses
            if is_women and any(w in text_corpus for w in ["women", "female", "mahila", "woman"]):
                score += 20.0
                drivers.append("is_women_owned")
                reasons.append("offers preferential subsidy/allocation for women entrepreneurs")

            if social_cat in ["sc", "st"] and any(sc in text_corpus for sc in ["sc", "st", "scheduled caste", "scheduled tribe", "special category"]):
                score += 18.0
                drivers.append(f"social_category ({social_cat})")
                reasons.append(f"provides enhanced support margins for {social_cat.upper()} promoters")

            if is_rural and any(r in text_corpus for r in ["rural", "gramin", "village", "backward"]):
                score += 10.0
                drivers.append("is_rural_enterprise")
                reasons.append("rural area priority incentive applicable")

            if is_startup and any(st in text_corpus for st in ["startup", "seed", "innovation", "dpiit"]):
                score += 10.0
                drivers.append("is_startup_recognized")
                reasons.append("startup venture component applicable")

            # 4. Benefit richness & financial support
            benefit_count = len(s.benefits)
            if benefit_count >= 2:
                score += min(benefit_count * 4.0, 16.0)

            # 5. Type preferences: Subsidies and Credit Guarantees preferred over generic schemes
            if s.knowledge_type == "SUBSIDY":
                score += 8.0
            elif s.knowledge_type == "LOAN":
                score += 5.0

            # 6. Strict State / Regional Geographic Scope Filtering
            user_state_clean = (loc.get("state") or "").strip().lower()
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

            detected_state = None
            text_and_url = f"{s.title} {s.snippet} {s.official_url} {s.organization}".lower()
            for region_key, aliases in REGIONAL_SCOPES.items():
                if any(alias in text_and_url for alias in aliases):
                    detected_state = region_key
                    break

            if detected_state:
                user_matches = False
                if user_state_clean:
                    if user_state_clean == detected_state:
                        user_matches = True
                    elif detected_state == "ner" and any(alias in user_state_clean for alias in REGIONAL_SCOPES["ner"]):
                        user_matches = True
                    elif detected_state in REGIONAL_SCOPES and any(alias in user_state_clean for alias in REGIONAL_SCOPES[detected_state]):
                        user_matches = True

                if user_matches:
                    score += 25.0
                    drivers.append(f"state_alignment ({user_state_clean.title()})")
                    reasons.append(f"exclusive State Government incentive applicable in {user_state_clean.title()}")
                elif user_state_clean and user_state_clean not in ("india", "all", "national", ""):
                    # Strict disqualification: Scheme is designated for a different State/Region
                    score -= 80.0
                    reasons.append(f"restricted to {detected_state.title()} (ineligible in {user_state_clean.title()})")

            return score, drivers, reasons

        score_a, drivers_a, reasons_a = score_scheme(scheme_a)
        score_b, drivers_b, reasons_b = score_scheme(scheme_b)

        # Incorporate initial retrieval relevance
        score_a += scheme_a.retrieval_score * 10.0
        score_b += scheme_b.retrieval_score * 10.0

        # Logistic preference probability
        score_diff = score_a - score_b
        # Scale diff so ~10 point diff = 73% probability
        prob_a = float(1.0 / (1.0 + pow(2.71828, -score_diff / 10.0)))
        prob_a = max(0.05, min(0.95, prob_a))

        if abs(prob_a - 0.5) < 0.03:
            winner_id = None
            rationale = (
                f"Both '{scheme_a.title}' and '{scheme_b.title}' offer comparable relevance and benefits "
                f"for a {msme_class} {biz_type} business."
            )
            driving_attrs = list(set(drivers_a + drivers_b))
        elif prob_a > 0.5:
            winner_id = scheme_a.id
            key_reasons = "; ".join(reasons_a[:3]) or "higher alignment with business parameters"
            rationale = (
                f"'{scheme_a.title}' is preferred over '{scheme_b.title}' for {biz_name} "
                f"because it {key_reasons}."
            )
            driving_attrs = drivers_a or ["business_alignment"]
        else:
            winner_id = scheme_b.id
            key_reasons = "; ".join(reasons_b[:3]) or "higher alignment with business parameters"
            rationale = (
                f"'{scheme_b.title}' is preferred over '{scheme_a.title}' for {biz_name} "
                f"because it {key_reasons}."
            )
            driving_attrs = drivers_b or ["business_alignment"]

        differential = (
            f"Preference spread: {abs(prob_a - 0.5)*200:.1f}% confidence margin based on {len(driving_attrs)} profile attributes."
        )

        return PairwiseComparison(
            scheme_a_id=scheme_a.id,
            scheme_a_title=scheme_a.title,
            scheme_b_id=scheme_b.id,
            scheme_b_title=scheme_b.title,
            winner_id=winner_id,
            preference_probability=round(prob_a, 4),
            comparative_rationale=rationale,
            driving_attributes=driving_attrs,
            benefit_differential=differential,
        )

    async def _call_llm_pairwise(
        self,
        scheme_a: CandidateScheme,
        scheme_b: CandidateScheme,
        profile: Dict[str, Any],
    ) -> Optional[PairwiseComparison]:
        """Calls external LLM (Gemini, Claude, OpenAI) for structured pairwise comparison."""
        # Prompt formulation
        prompt = f"""
You are an expert Government Scheme Advisor for Indian MSMEs.
Evaluate which of these two government schemes provides greater financial benefit, eligibility feasibility, and strategic value for the given MSME business.

MSME Business Profile:
{json.dumps(profile, indent=2)}

Scheme A:
- Title: {scheme_a.title}
- Organization: {scheme_a.organization}
- Type: {scheme_a.knowledge_type}
- Details: {scheme_a.snippet}
- Stated Benefits: {scheme_a.benefits}
- Criteria: {scheme_a.eligibility_criteria}

Scheme B:
- Title: {scheme_b.title}
- Organization: {scheme_b.organization}
- Type: {scheme_b.knowledge_type}
- Details: {scheme_b.snippet}
- Stated Benefits: {scheme_b.benefits}
- Criteria: {scheme_b.eligibility_criteria}

Return a valid JSON object ONLY with the following schema:
{{
  "preference_probability": <float between 0.0 and 1.0; >0.5 means Scheme A wins, <0.5 means Scheme B wins, 0.5 is tie>,
  "winner": "<'scheme_a', 'scheme_b', or 'tie'>",
  "comparative_rationale": "<Concise 2-sentence explanation of why one scheme was preferred over the other for this specific business>",
  "driving_attributes": ["<profile attributes that influenced the decision, e.g. 'is_women_owned', 'micro_classification', 'manufacturing'>"]
}}
"""
        # If Gemini
        if self.settings.llm_provider == "gemini" and self.settings.gemini_api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.settings.gemini_api_key}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}},
                )
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_text)
                    prob = float(parsed.get("preference_probability", 0.5))
                    winner_id = scheme_a.id if prob > 0.5 else (scheme_b.id if prob < 0.5 else None)
                    return PairwiseComparison(
                        scheme_a_id=scheme_a.id,
                        scheme_a_title=scheme_a.title,
                        scheme_b_id=scheme_b.id,
                        scheme_b_title=scheme_b.title,
                        winner_id=winner_id,
                        preference_probability=round(prob, 4),
                        comparative_rationale=parsed.get("comparative_rationale", ""),
                        driving_attributes=parsed.get("driving_attributes", []),
                        benefit_differential="LLM evaluated head-to-head advantage.",
                    )
        return None
