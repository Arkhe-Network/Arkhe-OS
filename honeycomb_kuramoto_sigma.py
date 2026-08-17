#!/usr/bin/env python3
"""
AVALON HONEYCOMB KURAMOTO — ENTROPY PRODUCTION COMPUTATION
===========================================================
Fase 2 specification: rigorous computation of stochastic entropy
production Σ for the honeycomb Kuramoto network.

STATUS: Specification ready for execution when environment permits.
This file contains the complete algorithm; it has NOT been executed.
All data generation must be done at runtime — no hardcoded values.
"""

import numpy as np
import networkx as nx
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class KuramotoResult:
    """Results from a single trajectory."""
    Q: float                    # Charge (time-antisymmetric)
    Sigma: float                # Total entropy production
    theta_final: np.ndarray     # Final phases
    trajectory: Optional[np.ndarray] = None  # Full trajectory (optional)


class HoneycombKuramotoSigma:
    """
    Honeycomb network of Kuramoto oscillators with thermal noise.
    Computes the physical entropy production from the Langevin dynamics.

    Hamiltonian:
        H = -J Σ_{<i,j>} cos(θ_j - θ_i) + Σ_i ω_i θ_i

    Dynamics (overdamped Langevin):
        dθ_i = [ω_i + J Σ_j A_ij sin(θ_j - θ_i)] dt + √(2T) dW_i

    Entropy production (Stratonovich / Ito equivalent for additive noise):
        dΣ = (1/T) Σ_i (dθ_i - drift_i dt)^2 / (2 dt)
           = (1/T) Σ_i (√(2T) dW_i)^2 / (2 dt)
           = Σ_i dW_i^2 / dt

    In the continuum limit, Σ_i dW_i^2 / dt → N * t (by quadratic variation).
    For discrete time step dt:
        ΔΣ = Σ_i (noise_i)^2 / (2 T dt)
    """

    def __init__(self,
                 graph: nx.Graph,
                 J: float = 1.0,
                 T: float = 1.0,
                 omega_std: float = 0.1,
                 seed: Optional[int] = None):
        self.graph = graph
        self.N = graph.number_of_nodes()
        self.adj = nx.to_numpy_array(graph)
        self.J = J
        self.T = max(T, 1e-6)  # avoid division by zero
        self.omega = np.random.normal(0, omega_std, self.N)
        if seed is not None:
            np.random.seed(seed)

    def drift(self, theta: np.ndarray) -> np.ndarray:
        """Compute deterministic drift term."""
        # Vectorized: d_i = ω_i + J Σ_j A_ij sin(θ_j - θ_i)
        diff = theta[None, :] - theta[:, None]  # θ_j - θ_i at (i,j)
        coupling = self.J * np.sum(self.adj * np.sin(diff), axis=1)
        return self.omega + coupling

    def run_trajectory(self,
                       theta0: np.ndarray,
                       t_max: float = 10.0,
                       dt: float = 0.05,
                       store_trajectory: bool = False) -> KuramotoResult:
        """
        Run a single Langevin trajectory and compute Σ.

        Parameters:
            theta0: initial phases, shape (N,)
            t_max: total simulation time
            dt: time step
            store_trajectory: if True, store full theta(t)

        Returns:
            KuramotoResult with Q, Sigma, and final state
        """
        n_steps = int(t_max / dt)
        theta = np.zeros((n_steps, self.N))
        theta[0] = theta0

        noise_factor = np.sqrt(2 * self.T * dt)
        Sigma = 0.0

        if store_trajectory:
            traj = np.zeros((n_steps, self.N))
            traj[0] = theta0

        for i in range(n_steps - 1):
            d = self.drift(theta[i])
            noise = noise_factor * np.random.randn(self.N)

            # Update
            theta[i+1] = theta[i] + d * dt + noise
            # Wrap to [-π, π]
            theta[i+1] = np.mod(theta[i+1] + np.pi, 2*np.pi) - np.pi

            if store_trajectory:
                traj[i+1] = theta[i+1]

            # Entropy production increment
            # dΣ = Σ_k noise_k^2 / (2 T dt)
            Sigma += np.sum(noise**2) / (2 * self.T * dt)

        # Charge: time-antisymmetric observable
        # Q = mean phase displacement
        Q = np.mean(theta[-1] - theta[0])

        return KuramotoResult(
            Q=Q,
            Sigma=Sigma,
            theta_final=theta[-1],
            trajectory=traj if store_trajectory else None
        )

    def ensemble(self,
                 n_traj: int = 100,
                 t_max: float = 10.0,
                 dt: float = 0.05,
                 seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run ensemble of trajectories.

        Returns:
            Q_vals: array of charges
            Sigma_vals: array of entropy productions
        """
        np.random.seed(seed)
        Q_vals = []
        Sigma_vals = []

        for m in range(n_traj):
            theta0 = np.random.uniform(-np.pi, np.pi, self.N)
            result = self.run_trajectory(theta0, t_max, dt)
            Q_vals.append(result.Q)
            Sigma_vals.append(result.Sigma)

        return np.array(Q_vals), np.array(Sigma_vals)


def build_honeycomb(radius: int = 2) -> nx.Graph:
    """Build a finite honeycomb graph."""
    G = nx.hexagonal_lattice_graph(radius, radius, periodic=False)
    G = nx.convert_node_labels_to_integers(G)
    return G


# ============================================================
# INTEGRATION WITH TUT BOUND MODULE
# ============================================================
def compute_tut_for_honeycomb(J: float = 1.0,
                               T: float = 1.0,
                               t_max: float = 10.0,
                               dt: float = 0.05,
                               n_traj: int = 200,
                               seed: int = 42) -> dict:
    """
    Full pipeline: build honeycomb -> simulate ensemble -> compute TUT.

    Returns dict with all statistics.
    """
    from tut_bound_module import TUTBound

    G = build_honeycomb(radius=2)
    model = HoneycombKuramotoSigma(G, J=J, T=T, seed=seed)
    Q_vals, Sigma_vals = model.ensemble(n_traj=n_traj, t_max=t_max, dt=dt, seed=seed)

    tut = TUTBound(bootstrap_samples=500)
    result = tut.compute(Sigma_vals, Q_vals)

    return {
        'graph_nodes': G.number_of_nodes(),
        'graph_edges': G.number_of_edges(),
        'J': J,
        'T': T,
        't_max': t_max,
        'dt': dt,
        'n_traj': n_traj,
        'eps_sq_tut': result.eps_sq_tut,
        'eps_sq_observed': result.eps_sq_observed,
        'avg_sigma': result.avg_sigma,
        'bound_satisfied': result.bound_satisfied,
        'bootstrap_std': result.bootstrap_std,
    }


if __name__ == "__main__":
    print("Avalon Honeycomb Kuramoto — Entropy Production")
    print("=" * 50)
    print("STATUS: Specification ready. Execute when environment permits.")
    print("\nTo run:")
    print("    results = compute_tut_for_honeycomb(J=1.0, T=1.0, n_traj=500)")
    print("    print(results)")
