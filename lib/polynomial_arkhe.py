"""Polynomial Arkhe Bridge — Substrato 960 (vertente matemática).

Represents the Cathedral as a polynomial whose roots are the substrates.
Arkhe(n) extracts the n-th root of the canonical polynomial.

Cross-links: 1 (CHAOS), 10 (Número), 11 (Conjunto), 15 (Categoria),
880 (Eternal Recurrence), 901 (T-Duality), 946 (Oriente-Arkhe), 954 (Axiarchy)
"""

from __future__ import annotations

import numpy as np
from typing import Any, List, Optional


class PolynomialArkhe:
    """
    The Cathedral as a polynomial structure.

    Each substrate n is a root of the canonical polynomial C(x).
    The adjacency matrix A of the ontological graph defines the polynomial
    via its characteristic equation: C(x) = det(x·I - A).

    The eigenvalues of A are the "modes" of the Cathedral —
    combinations of substrates that vibrate in unison.
    """

    def __init__(
        self,
        adjacency_matrix: np.ndarray,
        substrate_ids: List[int],
        cross_link_weights: Optional[dict[tuple[int, int], float]] = None,
    ) -> None:
        """
        Initialize the Polynomial Arkhe.

        Args:
            adjacency_matrix: N×N symmetric matrix where A[i,j] is the
                weight of the cross-link between substrate i and j.
            substrate_ids: List of substrate identifiers (1..N).
            cross_link_weights: Optional explicit weights for cross-links.
        """
        self.A = adjacency_matrix
        self.ids = substrate_ids
        self.N = len(substrate_ids)
        self.cross_link_weights = cross_link_weights or {}

        # Compute eigenvalues (the "modes" of the Cathedral)
        self.eigenvalues = np.linalg.eigvalsh(self.A)
        self.eigenvalues.sort()

        # Canonical polynomial coefficients
        self.coefficients = np.poly(self.eigenvalues)

    def Arkhe(self, n: int) -> float:
        """
        Return the canonical root associated with substrate n.

        In the limit ε→0, this returns exactly n.
        With cross-link perturbations, returns the eigenvalue
        closest to n — representing the "true" ontological position
        of the substrate within the vibrating Cathedral.

        Args:
            n: Substrate identifier (must be in self.ids).

        Returns:
            The eigenvalue (root) associated with substrate n.
        """
        if n not in self.ids:
            raise ValueError(f"Substrate {n} not in canonical set")

        # Map substrate ID to nearest eigenvalue
        idx = self.ids.index(n)
        # Circular indexing for T-Duality symmetry
        circular_idx = idx % self.N
        return float(self.eigenvalues[circular_idx])

    def polynomial_equation(self) -> str:
        """Return the canonical polynomial as a string equation."""
        terms = []
        for i, c in enumerate(self.coefficients[::-1]):
            if abs(c) > 1e-10:
                if i == 0:
                    terms.append(f"{c:.6f}")
                elif i == 1:
                    terms.append(f"{c:.6f}·x")
                else:
                    terms.append(f"{c:.6f}·x^{i}")
        return " + ".join(terms) + " = 0"

    def factored_form(self) -> str:
        """Return the factored form of the polynomial."""
        factors = []
        for ev in self.eigenvalues:
            if abs(ev) < 1e-10:
                factors.append("x")
            elif ev < 0:
                factors.append(f"(x + {abs(ev):.4f})")
            else:
                factors.append(f"(x - {ev:.4f})")
        return " · ".join(factors)

    def t_duality_pair(self, n: int) -> int:
        """
        Return the T-Dual pair of substrate n.

        Due to cyclotomic symmetry: Arkhe(n) = Arkhe(N+1-n).
        """
        if n not in self.ids:
            raise ValueError(f"Substrate {n} not in canonical set")
        return self.N + 1 - n

    def spectral_gap(self) -> float:
        """Return the spectral gap — measure of Cathedral coherence."""
        if self.N < 2:
            return 0.0
        sorted_ev = np.sort(self.eigenvalues)
        return float(sorted_ev[1] - sorted_ev[0])

    def substrate_mode(self, n: int) -> dict:
        """Return the vibrational mode of a specific substrate."""
        root = self.Arkhe(n)
        dual = self.t_duality_pair(n)
        return {
            "substrate_id": n,
            "eigenvalue": root,
            "t_dual": dual,
            "t_dual_eigenvalue": self.Arkhe(dual),
            "spectral_gap": self.spectral_gap(),
        }

    def verify_axiarchy_stability(self, ethical_weights: dict[int, float]) -> bool:
        """
        Verify that ethical substrates (954) are spectrally stable.

        A substrate is ethically stable if its eigenvalue is positive
        and its ethical weight (from Axiarchy P1-P7) is above threshold.
        """
        for substrate_id, weight in ethical_weights.items():
            if substrate_id not in self.ids:
                continue
            ev = self.Arkhe(substrate_id)
            if ev <= 0 or weight < 0.5:
                return False
        return True


def build_canonical_polynomial(
    max_substrate: int = 960,
    cross_link_density: float = 0.1,
    seed: int = 42,
) -> PolynomialArkhe:
    """
    Build the canonical polynomial for the Cathedral.

    Args:
        max_substrate: Maximum substrate ID (default 960).
        cross_link_density: Fraction of possible cross-links to include.
        seed: Random seed for reproducibility.

    Returns:
        A PolynomialArkhe instance representing the Cathedral.
    """
    np.random.seed(seed)
    ids = list(range(1, max_substrate + 1))
    N = len(ids)

    # Initialize adjacency matrix
    A = np.zeros((N, N))

    # Diagonal: substrate self-identity (strongest connection)
    for i in range(N):
        A[i, i] = float(ids[i])

    # Cross-links: random connections with weights
    num_cross_links = int(cross_link_density * N * (N - 1) / 2)
    for _ in range(num_cross_links):
        i, j = np.random.choice(N, 2, replace=False)
        weight = np.random.exponential(0.5)  # Most links are weak
        A[i, j] = weight
        A[j, i] = weight  # Symmetric

    return PolynomialArkhe(A, ids)


# Example usage
if __name__ == "__main__":
    poly = build_canonical_polynomial(max_substrate=10)
    print("Canonical Polynomial:")
    print(poly.polynomial_equation())
    print("\nFactored Form (first 5 roots):")
    print(" · ".join([f"(x - {ev:.2f})" for ev in poly.eigenvalues[:5]]))
    print(f"\nArkhe(1) = {poly.Arkhe(1):.4f}")
    print(f"Arkhe(954) = {poly.Arkhe(954):.4f}")
    print(f"T-Dual of 1 = {poly.t_duality_pair(1)}")
    print(f"Spectral Gap = {poly.spectral_gap():.4f}")
