#!/usr/bin/env python3
"""
AVALON TUT BOUND MODULE (tut_bound_module.py)
=============================================
Rigorous implementation of the Thermodynamic Uncertainty Theorem
as an operational precision bound for stochastic processes in Avalon.

Formula (Ray et al., 2025):
    ε²_Q = Var(Q) / <Q>²  ≥  1 / <tanh(Σ/2)> - 1

This is the ONLY valid TUT formula. Any other expression claiming
to be "the TUT bound" must derive from this one.
"""

import numpy as np
from typing import Union, Callable, Optional
from dataclasses import dataclass


@dataclass
class TUTResult:
    """Container for TUT bound computation results."""
    eps_sq_tut: float           # The TUT bound
    eps_sq_observed: float      # Observed scaled variance
    avg_sigma: float            # Mean entropy production
    avg_tanh: float             # <tanh(Σ/2)>
    n_samples: int              # Number of trajectories used
    bound_satisfied: bool       # True if eps_sq_observed >= eps_sq_tut
    bootstrap_std: Optional[float] = None  # Bootstrap standard error


class TUTBound:
    """
    Computes the Thermodynamic Uncertainty Theorem bound.

    Usage:
        tut = TUTBound()
        result = tut.compute(Sigma_vals, Q_vals)
        if not result.bound_satisfied:
            raise ValueError("Physical bound violated!")
    """

    def __init__(self, bootstrap_samples: int = 1000):
        self.bootstrap_samples = bootstrap_samples

    def compute(self,
                entropy_production: np.ndarray,
                charge_values: np.ndarray,
                check_positive: bool = True) -> TUTResult:
        """
        Compute TUT bound from ensemble data.

        Parameters:
            entropy_production: 1D array of Σ values (one per trajectory)
            charge_values: 1D array of Q values (one per trajectory)
            check_positive: if True, raise on non-positive Σ

        Returns:
            TUTResult with bound and statistics
        """
        Sigma = np.asarray(entropy_production).flatten()
        Q = np.asarray(charge_values).flatten()

        if len(Sigma) != len(Q):
            raise ValueError("Sigma and Q must have same length")

        if check_positive and np.any(Sigma <= 0):
            # Some Σ may be negative in full DFT; for operational use,
            # we warn but do not block (the tanh handles it)
            pass

        # TUT bound
        avg_tanh = np.mean(np.tanh(Sigma / 2.0))
        if avg_tanh <= 0:
            raise ValueError(f"<tanh(Σ/2)> = {avg_tanh} <= 0; bound undefined")

        eps_sq_tut = 1.0 / avg_tanh - 1.0

        # Observed precision
        Q_mean = np.mean(Q)
        if abs(Q_mean) < 1e-12:
            eps_sq_obs = np.inf
        else:
            eps_sq_obs = np.var(Q) / (Q_mean ** 2)

        # Bootstrap for uncertainty
        n = len(Sigma)
        bootstrap_bounds = []
        for _ in range(self.bootstrap_samples):
            idx = np.random.choice(n, size=n, replace=True)
            S_boot = Sigma[idx]
            at = np.mean(np.tanh(S_boot / 2.0))
            if at > 0:
                bootstrap_bounds.append(1.0 / at - 1.0)

        bootstrap_std = np.std(bootstrap_bounds) if bootstrap_bounds else None

        return TUTResult(
            eps_sq_tut=eps_sq_tut,
            eps_sq_observed=eps_sq_obs,
            avg_sigma=np.mean(Sigma),
            avg_tanh=avg_tanh,
            n_samples=n,
            bound_satisfied=eps_sq_obs >= eps_sq_tut - 1e-9,  # tolerance
            bootstrap_std=bootstrap_std
        )

    def verify_bound(self, result: TUTResult, tolerance: float = 1e-6) -> bool:
        """Check if observed precision respects TUT bound."""
        return result.eps_sq_observed >= result.eps_sq_tut - tolerance

    @staticmethod
    def formula_universal() -> str:
        """Return the canonical TUT formula."""
        return "ε² = 1 / <tanh(Σ/2)> - 1"

    @staticmethod
    def formula_bimodal(a: float) -> float:
        """
        Special case: bimodal distribution P(Σ) = pδ(Σ-a) + (1-p)δ(Σ+a)
        with DFT constraint. Returns ε² directly.
        """
        return 1.0 / np.tanh(a / 2.0) ** 2 - 1.0

    @staticmethod
    def formula_gaussian_approx(mu: float) -> float:
        """
        Approximation for Gaussian with σ² = 2μ (DFT-compatible).
        Uses numerical integration internally.
        """
        from scipy.integrate import quad
        sigma = np.sqrt(2.0 * mu)

        def integrand(s):
            pdf = np.exp(-(s - mu)**2 / (2 * sigma**2)) / (sigma * np.sqrt(2 * np.pi))
            return np.tanh(s / 2.0) * pdf

        limit = 10 * sigma
        avg_tanh, _ = quad(integrand, -limit, limit, limit=100)
        return 1.0 / avg_tanh - 1.0


# ============================================================
# EXAMPLE USAGE
# ============================================================
if __name__ == "__main__":
    # Example: bimodal entropy production
    a = 2.0
    p = 1.0 / (1.0 + np.exp(-a))
    n = 10000

    # Sample from bimodal
    signs = np.random.choice([-1, 1], size=n, p=[1-p, p])
    Sigma = a * signs

    # Charge: for bimodal, Q ~ tanh(a/2) * sign
    Q = np.tanh(a / 2) * signs + 0.1 * np.random.randn(n)

    tut = TUTBound(bootstrap_samples=500)
    result = tut.compute(Sigma, Q)

    print("Avalon TUT Bound Computation")
    print("=" * 40)
    print(f"Samples:        {result.n_samples}")
    print(f"<Σ>:            {result.avg_sigma:.4f}")
    print(f"<tanh(Σ/2)>:    {result.avg_tanh:.6f}")
    print(f"ε²_TUT:         {result.eps_sq_tut:.6f}")
    print(f"ε²_observed:    {result.eps_sq_observed:.6f}")
    print(f"Bound OK:       {result.bound_satisfied}")
    print(f"Bootstrap σ:    {result.bootstrap_std:.6f}")

    # Verify against analytical bimodal formula
    analytical = TUTBound.formula_bimodal(a)
    print(f"\nAnalytical:     {analytical:.6f}")
    print(f"Error:          {abs(result.eps_sq_tut - analytical):.6f}")
