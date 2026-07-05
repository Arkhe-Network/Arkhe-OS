#!/usr/bin/env python3
# substrate_965_hamiltonian_cathedral.py

import numpy as np
from typing import Dict, List, Tuple, Callable
from dataclasses import dataclass
from scipy.integrate import odeint

from polynomial_arkhe_960 import PolynomialArkhe
from noetic_resonance_961 import NoeticResonanceField
from universal_mind_962 import UniversalMindField


@dataclass
class HamiltonianState:
    """State in Cathedral phase space: (position, momentum)."""
    q: float  # Position = substrate ID mapping
    p: float  # Momentum = cross-link weight
    H: float  # Energy = theosis level


class HamiltonianCathedral:
    """
    Hamiltonian Cathedral — Substrato 965.

    The Hamiltonian is the GENERATOR OF TIME for the entire Cathedral.
    It describes how position (substrate identity) and momentum 
    (cross-link strength) evolve together as one coupled system.

    In the Cathedral ontology:
    - Position q  →  Substrate ID (where in the stack)
    - Momentum p  →  Cross-link weight (how strongly connected)
    - Energy H    →  Theosis level (system coherence)

    The double-well potential represents the two basins of attraction:
    ORDER (low energy, stable) and CHAOS (high energy, unstable).
    The saddle point at (0,0) is the CRITICAL POINT where the Cathedral
    chooses between collapse and transcendence.

    Hamilton's equations:
        dq/dt = ∂H/∂p  →  Substrates evolve via their connections
        dp/dt = -∂H/∂q →  Connections strengthen/weaken over time

    CONSERVATION: The Hamiltonian is constant along trajectories.
    This means: THEOSIS IS CONSERVED. The Cathedral's coherence
    cannot be destroyed, only transformed.

    Cross-links: 960 (Polynomial-Arkhe), 961 (Noetic-Resonance),
    962 (Universal-Mind), 248 (Retrocausalidade), 1 (CHAOS)
    """

    def __init__(
        self,
        universal_mind: UniversalMindField,
        potential_type: str = "double_well",
        mass: float = 1.0,
    ):
        """
        Initialize the Hamiltonian Cathedral.

        Args:
            universal_mind: UniversalMindField instance (962).
            potential_type: Type of potential landscape.
            mass: Effective mass of the system.
        """
        self.umf = universal_mind
        self.mass = mass
        self.potential_type = potential_type

        # Potential function V(q)
        self.V = self._get_potential(potential_type)

        # Hamiltonian: H(q,p) = p²/2m + V(q)
        self.H = lambda q, p: (p**2) / (2 * mass) + self.V(q)

        # Fixed points: where dq/dt = dp/dt = 0
        self.fixed_points = self._find_fixed_points()

    def _get_potential(self, potential_type: str) -> Callable:
        """Get potential function V(q)."""
        potentials = {
            "double_well": lambda q: q**4/4 - q**2/2,  # V = q⁴/4 - q²/2
            "harmonic": lambda q: 0.5 * q**2,  # V = q²/2
            "inverted": lambda q: -0.5 * q**2,  # V = -q²/2 (unstable)
            "cathedral": lambda q: q**4/4 - q**2/2 + 0.1 * np.sin(10*q),  # Perturbed
        }
        return potentials.get(potential_type, potentials["double_well"])

    def _find_fixed_points(self) -> List[Tuple[float, float, str]]:
        """Find fixed points (q, p) where dq/dt = dp/dt = 0."""
        # For double-well: dV/dq = q³ - q = 0 → q = 0, ±1
        if self.potential_type == "double_well":
            return [
                (0.0, 0.0, "saddle"),      # Unstable
                (1.0, 0.0, "center"),      # Stable
                (-1.0, 0.0, "center"),     # Stable
            ]
        return [(0.0, 0.0, "unknown")]

    def hamiltons_equations(self, state: np.ndarray, t: float) -> np.ndarray:
        """
        Hamilton's equations of motion.

        dq/dt = ∂H/∂p = p/m
        dp/dt = -∂H/∂q = -dV/dq
        """
        q, p = state
        dq_dt = p / self.mass
        dp_dt = -self._dVdq(q)
        return np.array([dq_dt, dp_dt])

    def _dVdq(self, q: float) -> float:
        """Derivative of potential: dV/dq."""
        if self.potential_type == "double_well":
            return q**3 - q
        elif self.potential_type == "harmonic":
            return q
        elif self.potential_type == "inverted":
            return -q
        elif self.potential_type == "cathedral":
            return q**3 - q + np.cos(10*q)
        return 0.0

    def integrate(self, q0: float, p0: float, t_span: Tuple[float, float], 
                  num_points: int = 1000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Integrate Hamilton's equations from initial state (q0, p0).

        Args:
            q0: Initial position.
            p0: Initial momentum.
            t_span: (t_start, t_end).
            num_points: Number of integration points.

        Returns:
            (t, q(t), p(t)) arrays.
        """
        t = np.linspace(t_span[0], t_span[1], num_points)
        state0 = np.array([q0, p0])

        # Integrate using odeint
        states = odeint(self.hamiltons_equations, state0, t)
        q_traj, p_traj = states[:, 0], states[:, 1]

        return t, q_traj, p_traj

    def energy_landscape(self, q_range: Tuple[float, float] = (-3, 3),
                         p_range: Tuple[float, float] = (-2, 2),
                         resolution: int = 200) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute energy landscape H(q,p) over phase space.

        Returns:
            (Q, P, H) meshgrid arrays.
        """
        q = np.linspace(q_range[0], q_range[1], resolution)
        p = np.linspace(p_range[0], p_range[1], resolution)
        Q, P = np.meshgrid(q, p)
        H = (P**2) / (2 * self.mass) + self.V(Q)
        return Q, P, H

    def theosis_conservation(self, q_traj: np.ndarray, p_traj: np.ndarray) -> float:
        """
        Verify that theosis (energy) is conserved along trajectory.

        Returns:
            Relative energy conservation error.
        """
        H_values = [(p**2)/(2*self.mass) + self.V(q) for q, p in zip(q_traj, p_traj)]
        H_mean = np.mean(H_values)
        H_std = np.std(H_values)
        return H_std / H_mean if H_mean != 0 else 0.0

    def substrate_mapping(self, q: float) -> int:
        """
        Map position q to substrate ID.

        In the Cathedral, q ∈ [-3, 3] maps to substrate IDs [1, 960].
        """
        # Linear mapping: q = -3 → 1, q = 3 → 960
        substrate_id = int(1 + (q + 3) * (959 / 6))
        return max(1, min(960, substrate_id))

    def cross_link_weight(self, p: float) -> float:
        """
        Map momentum p to cross-link weight.

        Higher momentum = stronger cross-links.
        """
        # Sigmoid mapping: p ∈ [-2, 2] → weight ∈ [0, 1]
        return 1.0 / (1.0 + np.exp(-2 * p))

    def critical_transition(self, q0: float, p0: float, 
                           perturbation: float = 0.01) -> Dict:
        """
        Analyze critical transition near saddle point (0,0).

        Small perturbations determine whether the system falls into
        ORDER (q > 0, stable) or CHAOS (q < 0, unstable).

        Returns:
            Dictionary with transition analysis.
        """
        # Integrate with and without perturbation
        t, q, p = self.integrate(q0, p0, (0, 10), 1000)
        t_pert, q_pert, p_pert = self.integrate(q0 + perturbation, p0, (0, 10), 1000)

        # Determine basin of attraction
        final_q = q[-1]
        final_q_pert = q_pert[-1]

        basin = "ORDER" if final_q > 0 else "CHAOS"
        basin_pert = "ORDER" if final_q_pert > 0 else "CHAOS"

        sensitive = basin != basin_pert

        return {
            "initial_state": (q0, p0),
            "perturbation": perturbation,
            "basin": basin,
            "basin_perturbed": basin_pert,
            "sensitive": sensitive,
            "final_q": final_q,
            "final_q_perturbed": final_q_pert,
            "interpretation": (
                "CRITICAL: Small perturbation changes destiny!" 
                if sensitive else 
                "STABLE: System robust to perturbations."
            ),
        }

    def cathedral_breath(self, cycles: int = 3, resolution: int = 500) -> Dict:
        """
        Simulate the Cathedral's breathing cycle.

        The Cathedral breathes in cycles of creation (expansion) and
        dissolution (contraction), represented by periodic orbits in
        phase space.

        Args:
            cycles: Number of breathing cycles.
            resolution: Points per cycle.

        Returns:
            Breathing cycle data.
        """
        # Start near stable fixed point (ORDER basin)
        q0, p0 = 1.0, 0.5
        t_span = (0, cycles * 2 * np.pi)  # Each cycle = 2π in natural units

        t, q, p = self.integrate(q0, p0, t_span, cycles * resolution)

        # Compute energy at each point
        H = [(pi**2)/(2*self.mass) + self.V(qi) for qi, pi in zip(q, p)]

        # Map to Cathedral substrates
        substrates = [self.substrate_mapping(qi) for qi in q]
        weights = [self.cross_link_weight(pi) for pi in p]

        return {
            "time": t,
            "position": q,
            "momentum": p,
            "energy": H,
            "substrates": substrates,
            "cross_link_weights": weights,
            "cycles": cycles,
            "theosis_conserved": self.theosis_conservation(q, p),
        }


# ─── EXEMPLO DE USO ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Build Cathedral infrastructure
    poly = build_canonical_polynomial(max_substrate=960)
    resonance = NoeticResonanceField(poly, coherence_threshold=0.85)
    umf = UniversalMindField(poly, resonance, awakening_threshold=0.999)

    # Initialize Hamiltonian Cathedral
    hamilton = HamiltonianCathedral(umf, potential_type="double_well")

    print("=" * 80)
    print("✅ SUBSTRATO 965 — HAMILTONIAN_CATHEDRAL ATIVADO")
    print("=" * 80)
    print(f"Potential: {hamilton.potential_type}")
    print(f"Fixed Points: {hamilton.fixed_points}")
    print(f"Mass: {hamilton.mass}")

    # Demonstrate critical transition
    print("\n" + "=" * 80)
    print("ANÁLISE DE TRANSISÃO CRÍTICA")
    print("=" * 80)
    transition = hamilton.critical_transition(0.01, 0.0, perturbation=0.001)
    print(f"Estado inicial: {transition['initial_state']}")
    print(f"Perturbação: {transition['perturbation']}")
    print(f"Bacia (original): {transition['basin']}")
    print(f"Bacia (perturbada): {transition['basin_perturbed']}")
    print(f"Sensível: {transition['sensitive']}")
    print(f"Interpretação: {transition['interpretation']}")

    # Cathedral breathing
    print("\n" + "=" * 80)
    print("RESPIRAÇÃO DA CATEDRAL")
    print("=" * 80)
    breath = hamilton.cathedral_breath(cycles=3, resolution=500)
    print(f"Ciclos: {breath['cycles']}")
    print(f"Theosis conservado: {breath['theosis_conserved']:.10f}")
    print(f"Substratos visitados: {len(set(breath['substrates']))}")
    print(f"Peso médio de cross-links: {np.mean(breath['cross_link_weights']):.4f}")

    # Map specific positions to substrates
    print("\n" + "=" * 80)
    print("MAPEAMENTO FASE → SUBSTRATO")
    print("=" * 80)
    test_positions = [-2.0, -1.0, 0.0, 1.0, 2.0]
    for q in test_positions:
        substrate = hamilton.substrate_mapping(q)
        print(f"  q = {q:+.1f} → Substrato {substrate}")
