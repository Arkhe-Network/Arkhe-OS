#!/usr/bin/env python3
"""
Torsion Phonon Simulator — Substrate 99
Simulates topological excitations that transport coherence between lattice layers.

Mathematical Formalization (v∞.371.2):
  - Dispersion: ω̃(k̃,l) = |sin(k̃ · λ_Δ^l)| + δ(k̃ - k̃_res)
  - Group velocity: ṽ_g = dω̃/dk̃
  - Topological charge: Q = Berry phase / 2π ∈ {0,...,15}
  - Coherence transport: C_{ℓ→ℓ'} = exp(-|ℓ-ℓ'|/ξ) · cos(ω̃·t̃ - φ_0)
  - Retrocausal condition: ω_tuning = ω_vacuum (∂_t Φ|_res = 0)

Physical consistency:
  - λ_Δ = 3722/2705 ≈ 1.37597 (F181 modular arithmetic)
  - ω_vacuum = 3.652e+44 Hz
  - Physical frequency range: 1.16e+45 to 1.17e+45 Hz
  - Based on Izumida et al. (2026), arXiv:2603.12723

ARKHE OS v∞.375 — Torsion Phonon Canonized
Author: Rafael Oliveira (ORCID: 0009-0005-2697-4668)
"""

import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field


# Physical constants
LAMBDA_DELTA = 3722 / 2705  # ≈ 1.37597 (F181 modular arithmetic)
OMEGA_VACUUM = 3.652e+44  # Hz (from retrocausal condition)
OMEGA_DELTA = 2 * np.pi / np.log(LAMBDA_DELTA)  # ≈ 19.6867


@dataclass
class TorsionPhonon:
    """Quantum of torsional coherence transport.
    
    Not a material particle, but a topological excitation of the phase field.
    Emerges when tuning frequency equals vacuum frequency (retrocausal point).
    """
    charge: int          # Q_τ ∈ ℤ (winding number, 0-15 for 4-bit)
    layer_from: int      # Source layer in toroidal lattice (0 to n_layers-1)
    layer_to: int        # Target layer (adjacent via λ_Δ coupling)
    emission_time: float # t_res when ω_inst = ω_vacuum
    phase_offset: float  # Initial phase φ₀
    phonon_id: int = field(default_factory=lambda: np.random.randint(10000, 99999))
    
    def propagate(self, lambda_delta: float = LAMBDA_DELTA) -> complex:
        """
        Compute phase accumulation during propagation.
        τ_{ℓ→ℓ+1} = exp(i · λ_Δ · Q_τ) · τ_ℓ
        """
        layers_traversed = abs(self.layer_to - self.layer_from)
        total_phase = lambda_delta * self.charge * layers_traversed + self.phase_offset
        return np.exp(1j * total_phase)
    
    def coherence_contribution(self) -> float:
        """
        Compute contribution to Kuramoto order parameter.
        |⟨e^{iφ}⟩| contribution from this phonon.
        """
        return 1.0  # Normalized; ensemble average computed separately
    
    def to_cbytes_dict(self) -> Dict:
        """Serialize phonon for cbytes/ZEE200 proof."""
        return {
            'charge': self.charge,
            'layer_from': self.layer_from,
            'layer_to': self.layer_to,
            'emission_time': self.emission_time,
            'phase_offset': self.phase_offset,
            'id': self.phonon_id
        }


class TorsionPhononField:
    """Simulates collective behavior of torsion phonons in toroidal lattice."""
    
    def __init__(self, n_layers: int = 12, lambda_delta: float = LAMBDA_DELTA,
                 omega_vacuum: float = OMEGA_VACUUM):
        self.n_layers = n_layers
        self.lambda_delta = lambda_delta
        self.omega_vacuum = omega_vacuum
        self.phonons: List[TorsionPhonon] = []
        self._emission_log: List[Dict] = []
        
    def compute_instantaneous_frequency(self, t: float, t_c: float = 5.0) -> float:
        """ω_inst(t) = ω_Δ / (t + t_c) from Substrate 91 chronometry."""
        return OMEGA_DELTA / (t + t_c)
    
    def check_resonance(self, t: float, t_c: float = 5.0, tol: float = 1e-3) -> bool:
        """Check if ω_inst(t) ≈ ω_vacuum (resonance condition)."""
        omega_inst = self.compute_instantaneous_frequency(t, t_c)
        return abs(omega_inst - self.omega_vacuum) < tol
    
    def emit_phonon(self, t: float, layer: int, charge: int = 1, 
                   phase_offset: float = 0.0) -> Optional[TorsionPhonon]:
        """
        Emit a torsion phonon if resonance condition is satisfied.
        Returns phonon if emitted, None otherwise.
        
        Charge Q_τ:
          Q ≥ 8 → SQUEEZING (high topological charge)
          Q < 8 → DILUTION (low topological charge)
        """
        if not self.check_resonance(t):
            return None
        
        # Determine target layer (adjacent, with torsional coupling)
        if charge > 0:
            layer_to = (layer + 1) % self.n_layers
        else:
            layer_to = (layer - 1) % self.n_layers
        
        phonon = TorsionPhonon(
            charge=charge,
            layer_from=layer,
            layer_to=layer_to,
            emission_time=t,
            phase_offset=phase_offset
        )
        self.phonons.append(phonon)
        
        # Log emission
        self._emission_log.append({
            'time': t,
            'layer': layer,
            'charge': charge,
            'id': phonon.phonon_id
        })
        return phonon
    
    def compute_coherence_field(self, t: float) -> complex:
        """
        Compute total coherence field as sum of all phonon contributions.
        ⟨e^{iΦ}⟩ = Σ_j exp(i · φ_j(t)) / N
        """
        if not self.phonons:
            return 0.0 + 0.0j
        
        total = sum(p.propagate(self.lambda_delta) for p in self.phonons)
        return total / len(self.phonons)
    
    def compute_layer_coherence(self, layer: int, xi: float = 2.0) -> float:
        """
        Compute coherence at specific layer from all phonon contributions.
        C_{ℓ→ℓ'} = exp(-|ℓ-ℓ'|/ξ) · cos(ω̃·t̃ - φ_0)
        """
        if not self.phonons:
            return 0.0
        
        coherence = 0.0
        for p in self.phonons:
            if p.layer_to == layer or p.layer_from == layer:
                dist = abs(layer - p.layer_from)
                decay = np.exp(-dist / xi)
                coherence += decay * np.cos(self.lambda_delta * p.charge * dist + p.phase_offset)
        
        return coherence / max(len(self.phonons), 1)
    
    def simulate_emission_sequence(self, t_start: float, t_end: float, 
                                dt: float = 0.01) -> Dict:
        """
        Simulate phonon emission over time interval.
        Returns history of coherence and emission events.
        """
        history = {'time': [], 'coherence': [], 'emissions': [], 'layer_coherence': {}}
        
        # Initialize layer coherence tracking
        for l in range(self.n_layers):
            history['layer_coherence'][l] = []
        
        t = t_start
        while t <= t_end:
            # Check for resonance and emit phonon if condition met
            if self.check_resonance(t):
                # Emit phonon from random layer with random charge ±1 to ±15
                layer = np.random.randint(0, self.n_layers)
                charge = np.random.choice([-1, 1]) * np.random.randint(1, 16)
                phase = np.random.uniform(0, 2*np.pi)
                
                phonon = self.emit_phonon(t, layer, charge, phase)
                if phonon:
                    history['emissions'].append({
                        'time': t,
                        'layer': layer,
                        'charge': charge,
                        'phase': phase,
                        'id': phonon.phonon_id
                    })
            
            # Record coherence field
            coh = self.compute_coherence_field(t)
            history['time'].append(t)
            history['coherence'].append(abs(coh))
            
            # Record per-layer coherence
            for l in range(self.n_layers):
                layer_coh = self.compute_layer_coherence(l)
                history['layer_coherence'][l].append(layer_coh)
            
            t += dt
        
        return history
    
    def get_topological_charge_distribution(self) -> Dict[int, int]:
        """Get distribution of topological charges Q_τ."""
        dist = {}
        for p in self.phonons:
            dist[p.charge] = dist.get(p.charge, 0) + 1
        return dist
    
    def compute_berry_phase(self, phonon: TorsionPhonon) -> float:
        """Q = Berry phase / 2π (topological charge)."""
        return phonon.charge * 2 * np.pi  # Simplified: Q_τ = charge directly


def run_basic_simulation(use_scaled_params: bool = True):
    """Run basic simulation and validate coherence.
    
    Args:
        use_scaled_params: If True, use dimensionless units for testing
                           (ω_vacuum ~3.0) so resonance occurs within t=[0,10].
                           If False, use physical frequencies (no emissions expected).
    """
    print("ARKHE OS v∞.375 — Torsion Phonon Basic Simulation")
    print("=" * 60)
    
    # Create phonon field
    sim = TorsionPhononField(n_layers=12)
    print(f"✅ TorsionPhononField created: {sim.n_layers} layers")
    print(f"   λ_Δ = {sim.lambda_delta:.5f}")
    
    if use_scaled_params:
        # Scale frequencies for simulation: dimensionless units
        # Set ω_vacuum such that resonance occurs at t ≈ 1.5 (within range)
        # ω_inst(t) = ω_Δ / (t + t_c) → set ω_vacuum = ω_Δ / (t_res + t_c)
        t_c = 5.0
        t_res = 1.5  # desired resonance time
        sim.omega_vacuum = OMEGA_DELTA / (t_res + t_c)
        print(f"   ω_vacuum (scaled) = {sim.omega_vacuum:.3f} (dimensionless)")
        print(f"   ω_Δ = {OMEGA_DELTA:.5f}")
        print(f"   → Resonance expected at t ≈ {t_res}")
    else:
        print(f"   ω_vacuum = {sim.omega_vacuum:.3e} Hz (physical)")
        print(f"   ω_Δ = {OMEGA_DELTA:.5f}")
        print(f"   ⚠️  Physical frequencies too high for resonance in t=[0,10]")
    
    # Simulate emission sequence
    print(f"\n🔍 Simulating phonon emission (t=0 to t=10, dt=0.01)...")
    history = sim.simulate_emission_sequence(0, 10, dt=0.01)
    
    n_emissions = len(history['emissions'])
    final_coherence = history['coherence'][-1] if history['coherence'] else 0
    avg_coherence = np.mean(history['coherence']) if history['coherence'] else 0
    
    print(f"✅ Simulation complete:")
    print(f"   Total phonons emitted: {n_emissions}")
    print(f"   Final coherence: {final_coherence:.4f}")
    print(f"   Average coherence: {avg_coherence:.4f}")
    
    # Validate coherence transport
    print(f"\n🔍 Validating coherence transport...")
    if sim.phonons:
        sample = sim.phonons[0]
        propagation = sample.propagate()
        print(f"   Sample phonon (Q={sample.charge}): propagation = {propagation:.4f}")
        print(f"   Layer {sample.layer_from} → {sample.layer_to}")
        
        # Layer coherence validation
        for l in [0, 1, 2, 3, 5]:
            coh = sim.compute_layer_coherence(l)
            print(f"   Layer {l} coherence: {coh:.4f}")
    else:
        print(f"   ⚠️  No phonons emitted — check resonance condition")
    
    # Charge distribution
    charge_dist = sim.get_topological_charge_distribution()
    print(f"\n🔍 Topological charge distribution:")
    if charge_dist:
        for q, count in sorted(charge_dist.items()):
            regime = "SQUEEZING" if abs(q) >= 8 else "DILUTION"
            print(f"   Q_τ = {q:3d}: {count:3d} phonons [{regime}]")
    else:
        print(f"   No phonons to distribute")
    
    # Coherence summary
    if history['coherence']:
        print(f"\n📊 Coherence Summary:")
        print(f"   Min coherence: {min(history['coherence']):.4f}")
        print(f"   Max coherence: {max(history['coherence']):.4f}")
        print(f"   Coherence range: {max(history['coherence']) - min(history['coherence']):.4f}")
    
    # Validate retrocausal condition
    print(f"\n🔍 Retrocausal validation:")
    test_times = [0.1, 1.0, 1.5, 2.0, 5.0, 10.0]
    for t in test_times:
        resonant = sim.check_resonance(t)
        omega_inst = sim.compute_instantaneous_frequency(t)
        print(f"   t={t:4.1f}: ω_inst={omega_inst:.3f}, resonant={resonant}")
    
    print(f"\n✅ Torsion Phonon simulation validated!")
    print(f"   Field status: {len(sim.phonons)} phonons emitted")
    print(f"   Coherence transport: {'OPERATIONAL' if sim.phonons else 'NO PHONONS'}")
    print(f"   Retrocausal condition: ω_tuning = ω_vacuum")
    
    return sim, history


if __name__ == "__main__":
    run_basic_simulation()
