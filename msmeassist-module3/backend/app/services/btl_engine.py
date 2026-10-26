"""
Bradley-Terry-Luce (BTL) Model & Maximum Likelihood Estimation (MLE) Engine.

Mathematical Formulation:
  P(item_i > item_j) = exp(theta_i) / (exp(theta_i) + exp(theta_j))
                     = pi_i / (pi_i + pi_j)
  where pi_i = exp(theta_i) > 0.

Estimation Algorithm:
  Solves the parameters pi_1, ..., pi_K via the Minorization-Maximization (MM)
  algorithm (Hunter 2004, Zermelo 1929) with Laplace/Dirichlet prior regularization.
  MM provides guaranteed monotonic convergence to the global maximum of the convex
  negative log-likelihood.
"""
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class BtlMleSolver:
    """
    Solves Bradley-Terry-Luce latent parameters using Maximum Likelihood Estimation.
    """

    def __init__(
        self,
        max_iterations: int = 200,
        tolerance: float = 1e-5,
        smoothing: float = 0.05,
    ):
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.smoothing = smoothing

    def fit(
        self,
        item_ids: List[str],
        win_matrix: np.ndarray,
    ) -> Tuple[Dict[str, float], Dict[str, float], int, bool, float]:
        """
        Fits BTL latent parameters via the Hunter Minorization-Maximization algorithm.

        Args:
            item_ids: Ordered list of item identifiers.
            win_matrix: 2D numpy array K x K where win_matrix[i, j] is the weight/wins
                        of item i over item j.

        Returns:
            Tuple of:
              - thetas: Dict of {item_id: zero-centered latent score theta_i}
              - probabilities: Dict of {item_id: normalized scale parameter pi_i}
              - iterations: Number of iterations to convergence
              - converged: True if converged within tolerance
              - log_likelihood: Final log-likelihood value
        """
        K = len(item_ids)
        if K == 0:
            return {}, {}, 0, True, 0.0
        if K == 1:
            return {item_ids[0]: 0.0}, {item_ids[0]: 1.0}, 0, True, 0.0

        W = np.array(win_matrix, dtype=np.float64)
        np.fill_diagonal(W, 0.0)

        # Apply Bayesian Laplace pseudocount smoothing to guarantee strong graph connectivity
        if self.smoothing > 0:
            pseudocount = self.smoothing / max(K - 1, 1)
            for i in range(K):
                for j in range(K):
                    if i != j:
                        W[i, j] += pseudocount

        # N[i, j] = total comparisons between i and j
        N = W + W.T

        # Wins for each item
        wins = np.sum(W, axis=1)

        # Initialize pi uniformly
        pi = np.ones(K, dtype=np.float64) / K

        converged = False
        iteration = 0

        for iteration in range(1, self.max_iterations + 1):
            pi_prev = pi.copy()
            pi_new = np.zeros(K, dtype=np.float64)

            # Hunter (2004) MM update step
            for i in range(K):
                denom = 0.0
                for j in range(K):
                    if i != j:
                        denom_pair = pi_prev[i] + pi_prev[j]
                        if denom_pair > 1e-12:
                            denom += N[i, j] / denom_pair

                pi_new[i] = wins[i] / (denom + 1e-12)

            # Normalize sum(pi) = 1.0
            sum_pi = np.sum(pi_new)
            if sum_pi > 0:
                pi_new /= sum_pi
            else:
                pi_new = np.ones(K, dtype=np.float64) / K

            # Check convergence in infinity-norm
            delta = np.max(np.abs(pi_new - pi_prev))
            pi = pi_new

            if delta < self.tolerance:
                converged = True
                break

        # Convert pi to zero-centered log-scale utility parameters theta_i
        log_pi = np.log(np.maximum(pi, 1e-12))
        thetas_raw = log_pi - np.mean(log_pi)

        # Calculate log-likelihood
        log_likelihood = 0.0
        for i in range(K):
            for j in range(i + 1, K):
                n_ij = N[i, j]
                if n_ij > 0:
                    prob_i = pi[i] / (pi[i] + pi[j] + 1e-12)
                    prob_j = 1.0 - prob_i
                    if W[i, j] > 0 and prob_i > 1e-12:
                        log_likelihood += W[i, j] * np.log(prob_i)
                    if W[j, i] > 0 and prob_j > 1e-12:
                        log_likelihood += W[j, i] * np.log(prob_j)

        thetas_dict = {item_ids[i]: float(thetas_raw[i]) for i in range(K)}
        prob_dict = {item_ids[i]: float(pi[i]) for i in range(K)}

        return thetas_dict, prob_dict, iteration, converged, float(log_likelihood)

    def compute_pairwise_probabilities(self, thetas: Dict[str, float]) -> Dict[Tuple[str, str], float]:
        """
        Computes P(A > B) for every pair based on fitted theta values.
        P(A > B) = 1 / (1 + exp(-(theta_A - theta_B)))
        """
        pair_probs = {}
        for a, theta_a in thetas.items():
            for b, theta_b in thetas.items():
                if a != b:
                    diff = theta_a - theta_b
                    prob = 1.0 / (1.0 + np.exp(-diff))
                    pair_probs[(a, b)] = float(prob)
        return pair_probs
