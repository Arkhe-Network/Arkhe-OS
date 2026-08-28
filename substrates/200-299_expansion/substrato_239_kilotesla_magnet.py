#!/usr/bin/env python3
"""
Substrato 239: Kilotesla Magnet Generator
Baseado em Patente CN119517538B (Huazhong University, 2025)
"Nanosecond grade kilotesla semi-destructive super-strong magnetic field generating device and method"
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy.integrate import solve_ivp
import json

# ============================================================================
# CONSTANTES
# ============================================================================

MU_0 = 4 * np.pi * 1e-7  # H/m

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class KiloteslaMagnetParams:
    """Parâmetros do gerador de campo magnético (Patente CN119517538B)."""
    # Geometria do solenóide
    inner_diameter: float = 4.0e-3  # m (4.0 mm)
    wire_cross_section: Tuple[float, float] = (0.5e-3, 0.5e-3)  # m (0.5×0.5 mm)
    axial_turns: int = 5  # [2,5] conforme patente
    radial_layers: int = 2  # [2,5]
    total_turns: int = 10

    # Circuito magnético (multi-stage magnetic compression)
    capacitance: float = 100e-9  # F (100 nF)
    voltage: float = 100e3  # V (100 kV)
    inductance: float = 1e-6  # H (~1 μH)

    # Magnetic switches (volt-second products)
    vs_first: float = 12e-3  # V·s (12 mVs)
    vs_second: float = 5e-3  # V·s (5 mVs)

    # Material
    conductor_material: str = "Cu"  # Cu, Ta, W

@dataclass
class MagneticPulse:
    """Pulso magnético."""
    time: np.ndarray
    current: np.ndarray
    voltage: np.ndarray
    magnetic_field: np.ndarray
    peak_field: float
    rise_time: float  # ns

# ============================================================================
# MODELO DE CIRCUITO DE COMPRESSÃO MAGNÉTICA (Patente CN119517538B)
# ============================================================================

class MagneticCompressionCircuit:
    """
    Circuito de compressão magnética multi-estágio.
    Baseado na patente CN119517538B (Huazhong University, 2025).
    """

    def __init__(self, params: KiloteslaMagnetParams):
        self.params = params
        self.solenoid = SolenoidModel(params)

    def simulate(self) -> MagneticPulse:
        """
        Simula a descarga do circuito de compressão magnética.

        Saída: pulso de corrente com rising edge nanossegundo,
        pico de 100-600 kA, tensão 10-100 kV.
        """
        # Modelo simplificado do circuito RLC com compressão
        C = self.params.capacitance
        L = self.params.inductance
        R = 0.01  # Ω (estimado)
        V0 = self.params.voltage

        # Equação do circuito: V = L*dI/dt + R*I + Q/C
        def circuit(t: float, state: np.ndarray) -> np.ndarray:
            Q, I = state
            dQ = I
            dI = (V0 - R*I - Q/C) / L
            return np.array([dQ, dI])

        # Condições iniciais
        y0 = np.array([0.0, 0.0])
        t_span = (0, 100e-9)  # 100 ns
        t_eval = np.linspace(t_span[0], t_span[1], 1000)

        sol = solve_ivp(circuit, t_span, y0, t_eval=t_eval,
                        method='RK45', rtol=1e-6, atol=1e-9)

        if sol.success:
            Q, I = sol.y
            V = V0 - Q/C - R*I

            # Calcula campo magnético no solenóide
            B = self.solenoid.field_from_current(I)

            # Encontra pico
            peak_idx = np.argmax(np.abs(I))
            peak_current = I[peak_idx]
            peak_field = B[peak_idx]

            # Rising edge (10% → 90%)
            threshold_10 = 0.1 * peak_current
            threshold_90 = 0.9 * peak_current
            idx_10 = np.where(I >= threshold_10)[0]
            idx_90 = np.where(I >= threshold_90)[0]
            rise_time = 0.0
            if len(idx_10) > 0 and len(idx_90) > 0:
                rise_time = (sol.t[idx_90[0]] - sol.t[idx_10[0]]) * 1e9  # ns

            return MagneticPulse(
                time=sol.t,
                current=I,
                voltage=V,
                magnetic_field=B,
                peak_field=peak_field,
                rise_time=rise_time
            )
        else:
            return MagneticPulse(
                time=np.array([]),
                current=np.array([]),
                voltage=np.array([]),
                magnetic_field=np.array([]),
                peak_field=0.0,
                rise_time=0.0
            )

# ============================================================================
# MODELO DE SOLENÓIDE (Patente CN119517538B)
# ============================================================================

class SolenoidModel:
    """
    Modelo de solenóide multicamadas para campos >1000 T.
    Baseado na patente CN119517538B.
    """

    def __init__(self, params: KiloteslaMagnetParams):
        self.params = params
        self._compute_geometry()

    def _compute_geometry(self):
        """Calcula geometria do solenóide."""
        # Dimensões do fio
        w, h = self.params.wire_cross_section

        # Raio médio
        self.r_mean = self.params.inner_diameter / 2 + (self.params.radial_layers * w) / 2

        # Comprimento do solenóide
        self.length = self.params.axial_turns * h

        # Número de voltas
        self.N = self.params.total_turns

    def inductance(self) -> float:
        """Indutância do solenóide (aproximação)."""
        # L ≈ μ₀ * N² * A / l (solenóide ideal)
        A = np.pi * self.r_mean**2
        return MU_0 * self.N**2 * A / self.length

    def field_from_current(self, current: np.ndarray) -> np.ndarray:
        """
        Campo magnético no centro do solenóide.
        B = μ₀ * N * I / L
        """
        return MU_0 * self.N * current / self.length

    def field_at_point(self, current: float, z: float, r: float) -> float:
        """
        Campo magnético em um ponto (z, r) do solenóide.
        Usa integração de Biot-Savart para solenóide finito.
        """
        # Implementação simplificada
        B0 = self.field_from_current(np.array([current]))[0]
        # Fator de correção para bordas
        f = 1.0 / (1 + (z / self.length)**2)
        return B0 * f

    def magnetic_pressure(self, current: float) -> float:
        """
        Pressão magnética radial (Patente CN119517538B).
        P = B² / (2μ₀)
        """
        B = self.field_from_current(np.array([current]))[0]
        return B**2 / (2 * MU_0)

    def deformation_time(self, current: float) -> float:
        """
        Tempo de deformação do solenóide (Patente).
        Quanto maior a corrente, mais rápido o solenóide é destruído.
        """
        # Estimado a partir da patente: para 600 kA, destruição em ~100 ns
        I_norm = current / 600e3
        return 100e-9 / (I_norm**2)  # s

# ============================================================================
# SUBSTRATO 239: INTEGRAÇÃO COM O CATEDRAL OS
# ============================================================================

class KiloteslaMagnetSubstrate:
    """Substrato 239: Kilotesla Magnet Generator."""

    def __init__(self, prolog_core):
        self.prolog = prolog_core
        self.params = KiloteslaMagnetParams()
        self.circuit = MagneticCompressionCircuit(self.params)
        self.solenoid = SolenoidModel(self.params)
        self.wormgraph = None
        self.pulses: List[MagneticPulse] = []
        self._register_prolog()

    def _register_prolog(self):
        if self.prolog:
            self.prolog.assertz("kilotesla_magnet_substrate('Substrate 239 v1.0')")
            self.prolog.assertz("kilotesla_magnet_materials([Cu, Ta, W])")

    def set_wormgraph(self, wormgraph):
        self.wormgraph = wormgraph

    def generate_pulse(self, voltage: float = 100e3,
                       capacitance: float = 100e-9) -> Dict:
        """
        Gera um pulso magnético (Patente CN119517538B).

        Args:
            voltage: tensão de carga (V), 10-100 kV
            capacitance: capacitância (F), ordem nF
        """
        self.params.voltage = voltage
        self.params.capacitance = capacitance
        self.circuit = MagneticCompressionCircuit(self.params)

        pulse = self.circuit.simulate()
        self.pulses.append(pulse)

        # Verifica se atingiu >1000 T
        achieved_kilotesla = pulse.peak_field >= 1000

        # Registra no WormGraph
        if self.wormgraph:
            self.wormgraph.commit({
                "event": "kilotesla_pulse",
                "pulse_number": len(self.pulses),
                "peak_field": pulse.peak_field,
                "peak_current": np.max(np.abs(pulse.current)),
                "rise_time": pulse.rise_time,
                "kilotesla_achieved": achieved_kilotesla
            })

        return {
            "status": "success",
            "pulse_number": len(self.pulses),
            "parameters": {
                "voltage": voltage / 1e3,
                "capacitance": capacitance * 1e9,
                "peak_current": np.max(np.abs(pulse.current)) / 1e3,
                "rise_time": pulse.rise_time
            },
            "magnetic_field": {
                "peak": pulse.peak_field,
                "kilotesla": pulse.peak_field / 1000,
                "achieved_1000T": achieved_kilotesla
            },
            "solenoid": {
                "inductance": self.solenoid.inductance() * 1e6,
                "turns": self.params.total_turns,
                "inner_diameter": self.params.inner_diameter * 1e3
            }
        }

    def optimize_for_kilotesla(self) -> Dict:
        """
        Otimiza parâmetros para alcançar >1000 T.
        Baseado na patente CN119517538B.
        """
        best_pulse = None
        best_field = 0.0
        best_params = None

        # Espaço de busca (patente)
        for V in np.linspace(50e3, 100e3, 6):
            for C in [50e-9, 100e-9, 150e-9]:
                for turns in [6, 8, 10, 12]:
                    # Atualiza parâmetros
                    self.params.voltage = V
                    self.params.capacitance = C
                    self.params.total_turns = turns
                    self.circuit = MagneticCompressionCircuit(self.params)

                    pulse = self.circuit.simulate()

                    if pulse.peak_field > best_field:
                        best_field = pulse.peak_field
                        best_pulse = pulse
                        best_params = {
                            'voltage': V,
                            'capacitance': C,
                            'turns': turns,
                            'peak_field': pulse.peak_field,
                            'peak_current': np.max(np.abs(pulse.current)),
                            'rise_time': pulse.rise_time
                        }

        return {
            "status": "success",
            "best_field": best_field,
            "best_field_kT": best_field / 1000,
            "best_params": best_params,
            "achieved_kilotesla": best_field >= 1000
        }

    def solenoid_design(self, target_field: float = 1000) -> Dict:
        """
        Projeta solenóide para campo alvo.
        """
        # Design baseado na patente
        # Para 1000 T: 10 voltas, 100 nF, 100 kV
        designs = []

        for N in [6, 8, 10, 12]:
            for D_inner in [3e-3, 4e-3, 5e-3]:
                self.params.total_turns = N
                self.params.inner_diameter = D_inner
                self.solenoid = SolenoidModel(self.params)
                self.circuit = MagneticCompressionCircuit(self.params)

                pulse = self.circuit.simulate()

                designs.append({
                    'turns': N,
                    'inner_diameter': D_inner * 1e3,
                    'peak_field': pulse.peak_field,
                    'peak_current': np.max(np.abs(pulse.current)) / 1e3,
                    'rise_time': pulse.rise_time,
                    'meets_target': pulse.peak_field >= target_field
                })

        return {
            "status": "success",
            "target_field": target_field,
            "designs": designs,
            "best_design": max(designs, key=lambda x: x['peak_field'])
        }

# ============================================================================
# PREDICADOS PROLOG
# ============================================================================

PROLOG_PREDICATES_239 = """
%%% ========================================================================
%%% SUBSTRATO 239: KILOTESLA MAGNET GENERATOR
%%% ========================================================================

:- dynamic magnet_pulse/5.
:- dynamic magnet_design/4.

magnet_register_pulse(ID, Field, Current, RiseTime, Kilotesla) :-
    assertz(magnet_pulse(ID, Field, Current, RiseTime, Kilotesla)),
    format('[Magnet] Pulse ~w: B=~2f T, rise=~2f ns~n', [ID, Field, RiseTime]).

magnet_register_design(Turns, Diameter, Field, Achieved) :-
    assertz(magnet_design(Turns, Diameter, Field, Achieved)).

magnet_best_field(Field) :-
    findall(F, magnet_pulse(_, F, _, _, _), Fields),
    max_list(Fields, Field).

magnet_kilotesla_pulses(IDs) :-
    findall(ID, magnet_pulse(ID, Field, _, _, true), Field >= 1000, IDs).

magnet_init :-
    retractall(magnet_pulse(_, _, _, _, _)),
    retractall(magnet_design(_, _, _, _)),
    format('[Magnet] Substrato 239 inicializado~n').
"""

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Inicializa substrato
    magnet = KiloteslaMagnetSubstrate(None)

    # Gera pulso (patente: 100 kV, 100 nF)
    pulse = magnet.generate_pulse(100e3, 100e-9)
    print(f"\n=== PULSO MAGNÉTICO ===")
    print(f"Campo de pico: {pulse['magnetic_field']['peak']:.0f} T ({pulse['magnetic_field']['kilotesla']:.2f} kT)")
    print(f"Corrente de pico: {pulse['parameters']['peak_current']:.1f} kA")
    print(f"Rising edge: {pulse['parameters']['rise_time']:.1f} ns")
    print(f"Atingiu 1000 T: {pulse['magnetic_field']['achieved_1000T']}")

    # Otimização
    opt = magnet.optimize_for_kilotesla()
    print(f"\n=== OTIMIZAÇÃO ===")
    print(f"Melhor campo: {opt['best_field']:.0f} T ({opt['best_field_kT']:.2f} kT)")
    print(f"Parâmetros: V={opt['best_params']['voltage']/1e3:.0f} kV, C={opt['best_params']['capacitance']*1e9:.0f} nF")
    print(f"Atingiu 1000 T: {opt['achieved_kilotesla']}")
