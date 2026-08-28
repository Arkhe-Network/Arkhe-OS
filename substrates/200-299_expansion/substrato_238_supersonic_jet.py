#!/usr/bin/env python3
"""
Substrato 238: Supersonic Plasma Jet Engine
Baseado em Hsu et al. (2026), "Experimental characterization of railgun-driven supersonic plasma jets"
PLX (Plasma Liner Experiment) - Los Alamos National Laboratory
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy.integrate import solve_ivp
import json

# ============================================================================
# CONSTANTES FÍSICAS (Hsu et al. 2026)
# ============================================================================

K_B = 1.380649e-23  # J/K
E_CHARGE = 1.602176634e-19  # C
M_ARGON = 6.6335e-26  # kg (massa de Ar)
GAMMA = 1.4  # índice politrópico (Murakami & Nishihara 2000)

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class PLXJetParams:
    """Parâmetros de jato de plasma para PLX (Hsu et al. 2026)."""
    # Parâmetros do jato (Tabela 2)
    electron_density: float = 2.0e16 * 1e6  # m⁻³ (2×10¹⁶ cm⁻³)
    electron_temperature: float = 1.4  # eV
    velocity: float = 30_000  # m/s (30 km/s)
    ionization_fraction: float = 0.96
    length: float = 0.20  # m (20 cm)
    diameter: float = 0.05  # m (5 cm)
    mach_number: float = 14.0

    # PLX Design (Cassibry et al. 2012)
    number_of_jets: int = 30
    chamber_radius: float = 1.11  # m (111 cm)
    merging_radius: float = 0.50  # m (50 cm)
    target_pressure: float = 1e8  # Pa (0.1-1 Mbar)

    # Diagnóstico (Merritt et al. 2012)
    interferometer_wavelength: float = 561e-9  # m (561 nm)
    interferometer_chords: List[float] = field(default_factory=lambda:
                                               [0.35, 0.413, 0.476, 0.540, 0.603, 0.667, 0.730, 0.794])

@dataclass
class PLXJet:
    """Jato de plasma no PLX (Hsu et al. 2026)."""
    velocity: float
    density: float
    temperature: float
    ionization: float
    length: float
    diameter: float
    mach: float
    mass: float
    momentum: float
    kinetic_energy: float

@dataclass
class PLXShot:
    """Disparo PLX (Hsu et al. 2026, shots 737-819)."""
    shot_number: int
    jet: PLXJet
    interferometer_phase: np.ndarray
    photodiode_signals: np.ndarray
    spectrometer_data: Dict
    time: np.ndarray
    gun_current: float

# ============================================================================
# MODELO DE EXPANSÃO DE JATO (Hsu et al. 2026, Sec. II.2)
# ============================================================================

class JetExpansionModel:
    """
    Modelo de expansão de jato supersônico.
    Baseado em Landau & Lifshitz (1987) e Hsu et al. (2026).
    """

    def __init__(self, params: PLXJetParams):
        self.params = params
        self.ion_sound_speed = self._compute_cs()

    def _compute_cs(self) -> float:
        """Velocidade do som iônico (Hsu et al. 2026)."""
        Te = self.params.electron_temperature * E_CHARGE  # J
        return np.sqrt(GAMMA * Te / M_ARGON)

    def radial_expansion_rate(self) -> float:
        """Taxa de expansão radial do jato (Landau & Lifshitz 1987)."""
        # Entre Cs (bulk) e 2Cs/(γ-1) (edges)
        return 2 * self.ion_sound_speed / (GAMMA - 1)

    def axial_expansion_rate(self) -> float:
        """Taxa de expansão axial do jato."""
        return self.radial_expansion_rate()

    def density_decay(self, distance: float) -> float:
        """
        Decaimento de densidade com a distância.
        Hsu et al. (2026): densidade cai ~1 ordem de magnitude em 40 cm.
        """
        # Volume aumenta com r² e L
        r0 = self.params.diameter / 2
        L0 = self.params.length

        # Expansão radial
        r_exp = r0 + self.radial_expansion_rate() * (distance / self.params.velocity)

        # Expansão axial
        L_exp = L0 + self.axial_expansion_rate() * (distance / self.params.velocity)

        # Conservação de massa
        V0 = np.pi * r0**2 * L0
        V = np.pi * r_exp**2 * L_exp

        return self.params.electron_density * V0 / V

    def merging_radius(self) -> float:
        """
        Raio de fusão de jatos (Cassibry et al. 2012, Eq. 1).
        Rm = [rj0(M√((γ-1)/2) + 1) + Rw] / [1 + (2/√N)(M√((γ-1)/2) + 1)]
        """
        rj0 = self.params.diameter / 2
        M = self.params.mach_number
        N = self.params.number_of_jets
        Rw = self.params.chamber_radius

        term = M * np.sqrt((GAMMA - 1) / 2) + 1

        Rm = (rj0 * term + Rw) / (1 + (2 / np.sqrt(N)) * term)
        return Rm

# ============================================================================
# DIAGNÓSTICOS PLX (Hsu et al. 2026, Sec. III.3)
# ============================================================================

class PLXDiagnostics:
    """
    Diagnósticos PLX: interferômetro, fotodiodo, espectrômetro.
    Baseado em Merritt et al. (2012), Lynn et al. (2010).
    """

    def __init__(self, params: PLXJetParams):
        self.params = params
        self.interferometer = EightChordInterferometer(params)

    def interferometer_phase(self, density: float, path_length: float,
                            ionization: float = 0.96) -> float:
        """
        Desvio de fase do interferômetro (Merritt et al. 2012, Eq. 2).
        Δφ = 9.2842e-16 * (f - 0.07235) * ∫ n_total dl
        """
        f = ionization
        n_total = density / f
        integral = n_total * path_length
        return 9.2842e-16 * (f - 0.07235) * integral

    def stark_broadening(self, n_e: float) -> float:
        """
        Largura de linha Hβ (Stehlé & Hutcheon 1999, Eq. 3).
        FWHM = 0.152 * (n_e / 1.5e13)^(2/3) * α1/2
        """
        n_e_cgs = n_e / 1e6  # cm⁻³
        alpha = 0.085
        return 0.152 * (n_e_cgs / 1.5e13)**(2/3) * alpha

    def photodiode_signal(self, intensity: float, distance: float) -> float:
        """Sinal de fotodiodo com atenuação 1/r²."""
        return intensity / (distance ** 2 + 1.0)

class EightChordInterferometer:
    """Interferômetro de 8 canais (Merritt et al. 2012)."""

    def __init__(self, params: PLXJetParams):
        self.params = params
        self.chords = params.interferometer_chords
        self.wavelength = params.interferometer_wavelength

    def measure(self, jet: PLXJet) -> np.ndarray:
        """Mede desvio de fase em cada corda."""
        phases = []
        for z in self.chords:
            # Densidade local
            n = self._density_at_z(jet, z)
            # Comprimento do caminho
            L = self._path_length(jet, z)
            # Desvio de fase
            phi = 9.2842e-16 * (jet.ionization - 0.07235) * n / jet.ionization * L
            phases.append(phi)
        return np.array(phases)

    def _density_at_z(self, jet: PLXJet, z: float) -> float:
        """Densidade na posição z (considerando expansão)."""
        # Baseado em Hsu et al. (2026): densidade cai 1 ordem em 40 cm
        decay = np.exp(-z / 0.15)  # 0.15 m = 15 cm
        return jet.density * (1 - 0.9 * (1 - decay))

    def _path_length(self, jet: PLXJet, z: float) -> float:
        """Comprimento do caminho na posição z."""
        # Diâmetro efetivo (expansão)
        D = jet.diameter * (1 + z / 0.50)
        return D

# ============================================================================
# SUBSTRATO 238: INTEGRAÇÃO COM O CATEDRAL OS
# ============================================================================

class SupersonicPlasmaJetSubstrate:
    """Substrato 238: Supersonic Plasma Jet Engine (PLX)."""

    def __init__(self, prolog_core):
        self.prolog = prolog_core
        self.params = PLXJetParams()
        self.expansion = JetExpansionModel(self.params)
        self.diagnostics = PLXDiagnostics(self.params)
        self.wormgraph = None
        self.shots: List[PLXShot] = []
        self._register_prolog()

    def _register_prolog(self):
        if self.prolog:
            self.prolog.assertz("supersonic_jet_substrate('Substrate 238 v1.0')")
            self.prolog.assertz("supersonic_jet_parameters([velocity, density, temperature, mach])")

    def set_wormgraph(self, wormgraph):
        self.wormgraph = wormgraph

    def create_jet(self, velocity: float = 30000,
                   density: float = 2e22,  # 2×10¹⁶ cm⁻³ → m⁻³
                   temperature: float = 1.4,
                   ionization: float = 0.96) -> PLXJet:
        """Cria um jato de plasma com parâmetros especificados."""
        mass = density * M_ARGON * np.pi * (self.params.diameter/2)**2 * self.params.length

        return PLXJet(
            velocity=velocity,
            density=density,
            temperature=temperature,
            ionization=ionization,
            length=self.params.length,
            diameter=self.params.diameter,
            mach=velocity / self.expansion.ion_sound_speed,
            mass=mass,
            momentum=mass * velocity,
            kinetic_energy=0.5 * mass * velocity**2
        )

    def propagate_jet(self, jet: PLXJet, distance: float) -> PLXJet:
        """
        Propaga o jato por uma distância (Hsu et al. 2026, Sec. IV.2).
        """
        # Densidade decai
        density_decay = self.expansion.density_decay(distance)

        # Velocidade constante (Hsu et al. 2026: ~30 km/s)
        velocity = jet.velocity

        # Temperatura (adiabática)
        V0 = np.pi * (jet.diameter/2)**2 * jet.length
        r_exp = jet.diameter/2 + self.expansion.radial_expansion_rate() * (distance / velocity)
        L_exp = jet.length + self.expansion.axial_expansion_rate() * (distance / velocity)
        V = np.pi * r_exp**2 * L_exp
        T_adiabatic = jet.temperature * (V0 / V)**(GAMMA - 1)

        return PLXJet(
            velocity=velocity,
            density=density_decay,
            temperature=T_adiabatic,
            ionization=jet.ionization,
            length=L_exp,
            diameter=2 * r_exp,
            mach=velocity / self.expansion.ion_sound_speed,
            mass=density_decay * M_ARGON * V,
            momentum=density_decay * M_ARGON * V * velocity,
            kinetic_energy=0.5 * density_decay * M_ARGON * V * velocity**2
        )

    def simulate_plx_shot(self) -> Dict:
        """
        Simula um disparo PLX (Hsu et al. 2026, shots 737-819).
        """
        # 1. Cria jato na saída do canhão
        jet = self.create_jet()

        # 2. Propaga até o ponto de fusão (R_m ≈ 50 cm)
        Rm = self.expansion.merging_radius()
        jet_propagated = self.propagate_jet(jet, Rm)

        # 3. Diagnósticos
        phases = self.diagnostics.interferometer.measure(jet_propagated)

        # 4. Registra disparo
        shot = PLXShot(
            shot_number=len(self.shots) + 1,
            jet=jet_propagated,
            interferometer_phase=phases,
            photodiode_signals=np.array([]),
            spectrometer_data={},
            time=np.linspace(0, 50e-6, 1000),
            gun_current=280e3  # kA (Hsu et al. 2026)
        )

        self.shots.append(shot)

        # Registra no WormGraph
        if self.wormgraph:
            self.wormgraph.commit({
                "event": "plx_shot",
                "shot_number": shot.shot_number,
                "velocity": jet_propagated.velocity / 1000,
                "density": jet_propagated.density / 1e6,
                "mach": jet_propagated.mach,
                "mass": jet_propagated.mass * 1e6,
                "merging_radius": Rm
            })

        return {
            "status": "success",
            "shot_number": shot.shot_number,
            "initial_jet": {
                "velocity": jet.velocity / 1000,
                "density": jet.density / 1e6,
                "temperature": jet.temperature,
                "mach": jet.mach,
                "mass": jet.mass * 1e6
            },
            "propagated_jet": {
                "velocity": jet_propagated.velocity / 1000,
                "density": jet_propagated.density / 1e6,
                "temperature": jet_propagated.temperature,
                "mach": jet_propagated.mach,
                "mass": jet_propagated.mass * 1e6,
                "length": jet_propagated.length * 100,
                "diameter": jet_propagated.diameter * 100
            },
            "merging_radius": Rm * 100,
            "interferometer_phases": phases.tolist()
        }

    def plx_design_validation(self) -> Dict:
        """
        Valida o design PLX (Cassibry et al. 2012, Hsu et al. 2012).
        """
        # Parâmetros de design PLX
        N = self.params.number_of_jets
        Rm = self.expansion.merging_radius()

        # Pressão de estagnação (Awe et al. 2011, Davis et al. 2012)
        # P_stag = ρ * V² / 2
        jet = self.create_jet()
        rho = jet.density * M_ARGON * jet.ionization
        P_stag = 0.5 * rho * jet.velocity**2

        # Pressão alvo: 0.1-1 Mbar
        P_target = self.params.target_pressure

        return {
            "status": "success",
            "number_of_jets": N,
            "merging_radius": Rm * 100,
            "stagnation_pressure": P_stag / 1e5,  # bar
            "target_pressure": P_target / 1e5,  # bar
            "achieved_target": P_stag >= P_target * 0.1,
            "design_parameters": {
                "jet_density": jet.density / 1e6,
                "jet_velocity": jet.velocity / 1000,
                "jet_mass": jet.mass * 1e6,
                "total_kinetic_energy": 0.5 * N * jet.mass * jet.velocity**2 / 1e3  # kJ
            }
        }

# ============================================================================
# PREDICADOS PROLOG
# ============================================================================

PROLOG_PREDICATES_238 = """
%%% ========================================================================
%%% SUBSTRATO 238: SUPERSONIC PLASMA JET ENGINE
%%% ========================================================================

:- dynamic plx_shot/5.
:- dynamic plx_jet/6.

plx_register_shot(ID, Velocity, Density, Mach, Mass, Radius) :-
    assertz(plx_shot(ID, Velocity, Density, Mach, Mass, Radius)),
    format('[PLX] Shot ~w: v=~2f km/s, M=~2f~n', [ID, Velocity/1000, Mach]).

plx_register_jet(ID, Velocity, Density, Temp, Mach, Mass) :-
    assertz(plx_jet(ID, Velocity, Density, Temp, Mach, Mass)).

plx_best_velocity(Velocity) :-
    findall(V, plx_shot(_, V, _, _, _, _), Velocities),
    max_list(Velocities, Velocity).

plx_avg_density(Density) :-
    findall(D, plx_shot(_, _, D, _, _, _), Densities),
    sum_list(Densities, Sum),
    length(Densities, N),
    Density is Sum / N.

plx_init :-
    retractall(plx_shot(_, _, _, _, _, _)),
    retractall(plx_jet(_, _, _, _, _, _)),
    format('[PLX] Substrato 238 inicializado~n').
"""

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Inicializa substrato
    plx = SupersonicPlasmaJetSubstrate(None)

    # Simula disparo PLX
    shot = plx.simulate_plx_shot()
    print(f"\n=== DISPARO PLX ===")
    print(f"Jato inicial: v={shot['initial_jet']['velocity']:.1f} km/s, M={shot['initial_jet']['mach']:.1f}")
    print(f"Jato propagado: v={shot['propagated_jet']['velocity']:.1f} km/s, M={shot['propagated_jet']['mach']:.1f}")
    print(f"Densidade: {shot['propagated_jet']['density']:.2e} cm⁻³")
    print(f"Raio de fusão: {shot['merging_radius']:.1f} cm")

    # Validação design PLX
    design = plx.plx_design_validation()
    print(f"\n=== DESIGN PLX ===")
    print(f"Número de jatos: {design['number_of_jets']}")
    print(f"Pressão de estagnação: {design['stagnation_pressure']:.2f} bar")
    print(f"Alvo: {design['target_pressure']:.2f} bar")
    print(f"Alcançado: {design['achieved_target']}")
