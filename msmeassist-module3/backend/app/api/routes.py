"""
API endpoints for Module 3 Explainable AI Recommendation Engine.
"""
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
import numpy as np

from app.models.schemas import (
    BtlSolveRequest,
    BtlSolveResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.btl_engine import BtlMleSolver
from app.services.recommendation_service import RecommendationService

router = APIRouter()
recommendation_service = RecommendationService()
btl_solver = BtlMleSolver()


@router.post("/api/recommendations/rank", response_model=RecommendationResponse, tags=["Recommendations"])
async def generate_recommendations(
    request: RecommendationRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Computes an Explainable AI recommendation ranking for an MSME business using:
      1. Candidate retrieval from RAG system
      2. Pairwise comparison against MSME profile attributes
      3. Bradley-Terry-Luce (BTL) Model parameter estimation via MLE
      4. Complete feature attribution and head-to-head win probability matrix
    """
    try:
        return await recommendation_service.generate_recommendations(request, auth_token=authorization)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation pipeline failed: {str(e)}")


@router.post("/api/recommendations/btl-solve", response_model=BtlSolveResponse, tags=["Statistical Engine"])
def solve_btl_matrix(payload: BtlSolveRequest):
    """
    Direct endpoint for solving the Bradley-Terry-Luce Model via Maximum Likelihood Estimation.
    Useful for testing, statistical validation, and arbitrary head-to-head tournament matrices.
    """
    items = payload.items
    W = np.array(payload.win_matrix, dtype=np.float64)

    if len(items) != W.shape[0] or len(items) != W.shape[1]:
        raise HTTPException(status_code=422, detail="win_matrix dimensions must match items length.")

    solver = BtlMleSolver(
        max_iterations=payload.max_iterations or 100,
        tolerance=payload.tolerance or 1e-6,
    )
    thetas, probs, iters, converged, log_lik = solver.fit(items, W)
    sorted_ranks = sorted(items, key=lambda x: thetas.get(x, 0.0), reverse=True)

    return BtlSolveResponse(
        items=items,
        thetas=thetas,
        probabilities=probs,
        ranks=sorted_ranks,
        iterations=iters,
        converged=converged,
        log_likelihood=round(log_lik, 4),
    )
