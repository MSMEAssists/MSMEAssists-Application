"""
Unit tests for the Bradley-Terry-Luce (BTL) Model and MLE Solver.
"""
import numpy as np
import pytest
from app.services.btl_engine import BtlMleSolver


def test_btl_solver_two_items():
    """Validates BTL closed-form solution for 2 items."""
    solver = BtlMleSolver(max_iterations=100, tolerance=1e-7, smoothing=0.0)
    items = ["SchemeA", "SchemeB"]
    # Scheme A wins 80 times, Scheme B wins 20 times against each other
    W = np.array([
        [0.0, 80.0],
        [20.0, 0.0],
    ])

    thetas, probs, iters, converged, log_lik = solver.fit(items, W)

    assert converged is True
    assert iters < 30
    assert thetas["SchemeA"] > thetas["SchemeB"]
    # Ratio pi_A / pi_B should be close to 80 / 20 = 4.0
    ratio = probs["SchemeA"] / probs["SchemeB"]
    assert pytest.approx(ratio, rel=0.05) == 4.0


def test_btl_solver_monotonicity():
    """Validates that items with strictly higher win counts receive higher latent theta."""
    solver = BtlMleSolver(max_iterations=100, tolerance=1e-6)
    items = ["TopScheme", "MidScheme", "LowScheme"]
    # Clear dominance hierarchy: Top > Mid > Low
    W = np.array([
        [0.0, 0.8, 0.9],
        [0.2, 0.0, 0.7],
        [0.1, 0.3, 0.0],
    ])

    thetas, probs, iters, converged, log_lik = solver.fit(items, W)

    assert converged is True
    assert thetas["TopScheme"] > thetas["MidScheme"] > thetas["LowScheme"]
    assert probs["TopScheme"] > probs["MidScheme"] > probs["LowScheme"]
    assert pytest.approx(sum(probs.values()), rel=1e-5) == 1.0


def test_btl_symmetric_ties():
    """Validates that equally matched items receive identical thetas."""
    solver = BtlMleSolver(max_iterations=100, tolerance=1e-6)
    items = ["Item1", "Item2", "Item3"]
    W = np.array([
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.5, 0.5, 0.0],
    ])

    thetas, probs, iters, converged, log_lik = solver.fit(items, W)

    assert converged is True
    assert pytest.approx(thetas["Item1"], abs=1e-3) == thetas["Item2"]
    assert pytest.approx(thetas["Item2"], abs=1e-3) == thetas["Item3"]
    assert pytest.approx(probs["Item1"], abs=1e-3) == 1.0 / 3.0


def test_btl_undefeated_smoothing():
    """Validates that undefeated items do not cause infinite theta divergence due to Laplace smoothing."""
    solver = BtlMleSolver(max_iterations=200, tolerance=1e-5, smoothing=0.05)
    items = ["Dominant", "Other1", "Other2"]
    W = np.array([
        [0.0, 1.0, 1.0],
        [0.0, 0.0, 0.5],
        [0.0, 0.5, 0.0],
    ])

    thetas, probs, iters, converged, log_lik = solver.fit(items, W)

    assert converged is True
    assert np.isfinite(thetas["Dominant"])
    assert thetas["Dominant"] > thetas["Other1"]


def test_pairwise_probability_computation():
    """Validates inverse logistic probability mapping P(A > B)."""
    solver = BtlMleSolver()
    thetas = {"A": 1.0, "B": 0.0}
    probs = solver.compute_pairwise_probabilities(thetas)

    p_a_b = probs[("A", "B")]
    p_b_a = probs[("B", "A")]

    assert pytest.approx(p_a_b + p_b_a, rel=1e-5) == 1.0
    assert p_a_b > 0.5
