"""
Integration tests for the end-to-end Explainable AI Recommendation pipeline.
"""
import pytest
from app.models.schemas import CandidateScheme, RecommendationRequest
from app.services.pairwise_evaluator import PairwiseEvaluator
from app.services.recommendation_service import RecommendationService


@pytest.mark.asyncio
async def test_pairwise_evaluator_women_owned_bias():
    """Validates that a women-owned business prefers a scheme with women-specific benefits."""
    evaluator = PairwiseEvaluator()

    scheme_women = CandidateScheme(
        id="scheme_women",
        title="Mahila Coir Yojana (Women Entrepreneur Subsidy)",
        organization="Coir Board",
        benefits=["Up to 75% subsidy for women entrepreneurs", "Skill training stipends"],
        eligibility_criteria=["Women artisans and micro units"],
    )

    scheme_general = CandidateScheme(
        id="scheme_general",
        title="General Tool Room Assistance",
        organization="Ministry of MSME",
        benefits=["Tooling facility access at concessional rates"],
        eligibility_criteria=["Any engineering unit"],
    )

    profile = {
        "business": {"name": "Lakshmi Enterprises", "type": "manufacturing"},
        "financial": {"msme_classification": "micro"},
        "characteristics": {"is_women_owned": True, "social_category": "general"},
    }

    comparison = await evaluator.evaluate_pair(scheme_women, scheme_general, profile)

    assert comparison.winner_id == "scheme_women"
    assert comparison.preference_probability > 0.5
    assert "is_women_owned" in comparison.driving_attributes
    assert "women" in comparison.comparative_rationale.lower()


@pytest.mark.asyncio
async def test_end_to_end_recommendation_pipeline():
    """Validates complete recommendation workflow: profile -> pairwise -> BTL -> XAI output."""
    service = RecommendationService()

    sample_profile = {
        "business": {"name": "Shree Balaji Fabrication", "type": "manufacturing", "industry": "Metal Works"},
        "financial": {"annual_turnover_inr": 3500000, "investment_inr": 1200000, "msme_classification": "micro"},
        "characteristics": {"is_women_owned": True, "social_category": "sc", "is_rural_enterprise": True},
        "location": {"state": "Karnataka", "district": "Mysuru", "area_type": "rural"},
    }

    request = RecommendationRequest(profile=sample_profile, top_k=5)
    response = await service.generate_recommendations(request)

    assert response.total_candidates == 5
    # For K=5, pairwise comparisons = 5 * 4 / 2 = 10
    assert response.pairwise_comparisons_count == 10
    assert response.btl_iterations > 0
    assert len(response.rankings) == 5

    # Check ranking structure
    top_rank = response.rankings[0]
    assert top_rank.rank == 1
    assert top_rank.theta_score >= response.rankings[1].theta_score
    assert top_rank.win_probability >= response.rankings[1].win_probability
    assert len(top_rank.key_comparative_advantage) > 10

    # Check pairwise matrix dimensions
    assert len(response.pairwise_matrix) == 5
    assert len(response.pairwise_matrix[0]) == 5

    # Check feature attributions
    assert "is_women_owned" in response.feature_importance_summary or "sector" in response.feature_importance_summary
