#!/usr/bin/env python3
"""
Substrato 237: Plasma Railgun Simulator (v2.0)
Baseado em "Design and Characterization of a Coaxial Plasma Railgun" (Coleman, 2021)
Integra: Modelo Snowplow, Instabilidades (Blow-by, Restrike), Erosão de Materiais
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from scipy.integrate import solve_ivp
from scipy.constants import mu_0, e, m_e, epsilon_0
import hashlib
import json
import time

# ============================================================================
# CONSTANTES FÍSICAS
# ============================================================================

MU_0 = mu_0  # 4π × 10⁻⁷ H/m
E_CHARGE = e  # 1.602 × 10⁻¹⁹ C
M_ELECTRON = m_e  # 9.109 × 10⁻³¹ kg
EPSILON_0 = epsilon_0  # 8.854 × 10⁻¹² F/m
M_ARGON = 6.63e-26  # kg (massa de um átomo de argônio)

# ============================================================================
# ESTRUTURAS DE DADOS
# ============================================================================

@dataclass
class CoaxialRailgunParams:
    """Parâmetros de projeto do canhão de plasma coaxial."""
    # Geometria (Coleman 2021)
    inner_radius: float = 0.00915  # m (1.83 cm diâmetro)
    outer_radius: float = 0.01165  # m (2.33 cm diâmetro)
    barrel_length: float = 0.18    # m (18 cm)
    electrode_ratio: float = 1.81  # outer_radius / inner_radius

    # Elétricos (PFN LC)
    capacitance: float = 58e-6     # F (58 μF)
    voltage: float = 7000.0        # V (7 kV típico)
    inductance: float = 0.5e-6     # H (estimado)
    resistance: float = 0.01       # Ω

    # Gás (Argônio)
    gas_mass: float = 4.3e-6       # kg (4.3 mg por pulso)
    gas_pressure: float = 6.89e5   # Pa (100 psi)
    gas_temperature: float = 300   # K

    # Materiais (Coleman: W-Cu 50/50, Macor)
    electrode_material: str = "CuW"  # CuW, Cu, CuW_LaB6
    insulator_material: str = "Macor"  # Macor, PEEK, Alumina

    # Diagnóstico
    interferometer_distance: float = 0.297  # m (29.7 cm)
    photodiode_positions: List[float] = field(default_factory=lambda: [0.328, 0.250])

@dataclass
class PlasmaJet:
    """Jato de plasma produzido pelo canhão coaxial."""
    velocity: float = 0.0          # m/s
    density: float = 0.0           # m⁻³
    temperature: float = 0.0       # K
    mass: float = 0.0              # kg
    radius: float = 0.0            # m
    length: float = 0.0            # m
    ionization_fraction: float = 0.96  # Coleman: ~96%
    electron_density: float = 0.0  # m⁻³
    mach_number: float = 14.0      # Hsu et al.

@dataclass
class RailgunShot:
    """Disparo completo do canhão."""
    shot_number: int
    voltage: float
    current: np.ndarray
    time: np.ndarray
    jets: List[PlasmaJet]
    line_integrated_density: np.ndarray
    photodiode_intensity: np.ndarray
    diagnostics: Dict
    blow_by_time: float = 0.0
    restrike_probability: float = 0.0

# ============================================================================
# MODELO SNOWPLOW (Rosenbluth 1954, Hart 1964, Coleman 2021)
# ============================================================================

class SnowplowModel:
    """
    Modelo snowplow para aceleração de plasma em canhão coaxial.

    Assumptions (Coleman 2021):
    1. Corrente se propaga como folha anular
    2. Folha "varre" gás neutro
    3. Sem campo magnético na frente da folha
    4. Massa acumulada conforme velocidade da folha
    """

    def __init__(self, params: CoaxialRailgunParams):
        self.params = params
        self.inductance_gradient = self._compute_inductance_gradient()

    def _compute_inductance_gradient(self) -> float:
        """L' = (μ₀ / 2π) * ln(b/a) (Coleman Eq. 2.1)"""
        return (MU_0 / (2 * np.pi)) * np.log(self.params.outer_radius / self.params.inner_radius)

    def _circuit_equation(self, t: float, Q: float, I: float, x: float, v: float) -> float:
        """Equação do circuito RLC com indutância variável (Coleman Eq. 2.2)"""
        L_total = self.params.inductance + self.inductance_gradient * x
        dI = (self.params.voltage - self.params.resistance*I - Q/self.params.capacitance -
              self.inductance_gradient * v * I) / L_total
        return dI

    def _snowplow_equations(self, t: float, state: np.ndarray) -> np.ndarray:
        """
        Equações diferenciais do snowplow.
        state = [x, v, m_acc, Q, I]
        x: posição da folha de corrente
        v: velocidade da folha
        m_acc: massa acumulada
        Q: carga no capacitor
        I: corrente
        """
        x, v, m_acc, Q, I = state

        # Indutância total
        L_total = self.params.inductance + self.inductance_gradient * x

        # Força magnética (Coleman Eq. 2.3)
        F_mag = 0.5 * self.inductance_gradient * I**2

        # Área anular
        A = np.pi * (self.params.outer_radius**2 - self.params.inner_radius**2)

        # Densidade do gás
        rho_gas = self.params.gas_mass / (A * self.params.barrel_length)

        # Taxa de acumulação de massa (snowplow)
        dm_dt = rho_gas * A * v if v > 0 else 0

        # Aceleração (Coleman Eq. 2.4)
        dv = F_mag / m_acc if m_acc > 0 else 0

        # Corrente e carga
        dQ = I
        dI = self._circuit_equation(t, Q, I, x, v)

        return np.array([v, dv, dm_dt, dQ, dI])

    def simulate(self, t_span: Tuple[float, float] = (0, 20e-6),
                 n_points: int = 10000) -> Dict:
        """
        Simula a aceleração do plasma.

        Args:
            t_span: intervalo de tempo (s)
            n_points: número de pontos de simulação

        Returns:
            Dict com resultados da simulação
        """
        # Condições iniciais (Coleman)
        A = np.pi * (self.params.outer_radius**2 - self.params.inner_radius**2)
        m_initial = self.params.gas_mass * 0.01  # 1% ionizado inicialmente

        y0 = np.array([0.0, 0.0, m_initial, 0.0, 0.0])
        t_eval = np.linspace(t_span[0], t_span[1], n_points)

        sol = solve_ivp(self._snowplow_equations, t_span, y0, t_eval=t_eval,
                        method='RK45', rtol=1e-6, atol=1e-9)

        if sol.success:
            x, v, m_acc, Q, I = sol.y

            # Velocidade de saída (quando x = barrel_length)
            idx_exit = np.searchsorted(x, self.params.barrel_length)
            if idx_exit < len(v):
                v_exit = v[idx_exit]
                m_exit = m_acc[idx_exit]
                t_exit = sol.t[idx_exit]
            else:
                v_exit = v[-1]
                m_exit = m_acc[-1]
                t_exit = sol.t[-1]

            return {
                'time': sol.t,
                'position': x,
                'velocity': v,
                'mass': m_acc,
                'charge': Q,
                'current': I,
                'exit_velocity': v_exit,
                'exit_mass': m_exit,
                'exit_time': t_exit,
                'peak_current': np.max(I),
                'success': True
            }
        else:
            return {'success': False, 'message': sol.message}

# ============================================================================
# MODELO DE INSTABILIDADES (Blow-by e Restrike)
# ============================================================================

class PlasmaInstabilityModel:
    """
    Modelo de instabilidades em canhões de plasma coaxial.
    Baseado em Cassidy et al. (2006), Parker (1989), Coleman (2021).
    """

    def __init__(self, params: CoaxialRailgunParams):
        self.params = params

    def blow_by_time(self, current: float) -> float:
        """
        Estima o tempo para desenvolvimento de blow-by.
        Cassidy et al. (2006) - Eq. simplificada.

        Blow-by ocorre quando a pressão magnética varia com 1/r²,
        fazendo com que o plasma próximo ao eletrodo interno acelere
        mais rápido que o externo.
        """
        I = max(current, 1.0)
        LnRatio = np.log(self.params.outer_radius / self.params.inner_radius)
        # Normalizado para 100 kA
        return 2.0 / (I/100000.0 * LnRatio)  # μs

    def blow_by_onset(self, current: float, time: float) -> bool:
        """Verifica se blow-by ocorreu."""
        t_bb = self.blow_by_time(current)
        return time > t_bb

    def restrike_probability(self, current: float, voltage: float) -> float:
        """
        Probabilidade de restrike baseada em Parker (1989).
        Restrike: arcos secundários que "roubam" corrente do arco primário.
        """
        I_norm = current / 100000.0
        V_norm = voltage / 10000.0
        prob = 0.1 * I_norm * V_norm
        return min(1.0, prob)

    def erosion_rate(self, material: str, current: float) -> float:
        """
        Taxa de erosão do eletrodo (g/C).
        Baseado em Lehr & Kristiansen (1989), Coleman (2021).

        Materiais testados por Coleman:
        - Cu: 1.58e-3 g/C (pior)
        - CuW: 1.24e-3 g/C (escolhido)
        - CuW_LaB6: 0.89e-3 g/C (melhor, mas mais caro)
        - CuW_Sb: 1.37e-3 g/C
        """
        rates = {
            'Cu': 1.58e-3,
            'CuW': 1.24e-3,
            'CuW_LaB6': 0.89e-3,
            'CuW_Sb': 1.37e-3
        }
        rate = rates.get(material, 1.24e-3)
        I_norm = current / 100000.0
        return rate * I_norm ** 0.8

# ============================================================================
# SUBSTRATO 237: INTEGRAÇÃO COM O CATEDRAL OS
# ============================================================================

class PlasmaRailgunSubstrate:
    """Substrato 237: Plasma Railgun Simulator."""

    def __init__(self, prolog_core):
        self.prolog = prolog_core
        self.params = CoaxialRailgunParams()
        self.snowplow = SnowplowModel(self.params)
        self.instability = PlasmaInstabilityModel(self.params)
        self.wormgraph = None
        self.shots: List[RailgunShot] = []
        self.materials_db = {
            'electrodes': {
                'Cu': {'cost': 1.0, 'erosion': 1.58e-3, 'machinability': 0.3},
                'CuW': {'cost': 2.5, 'erosion': 1.24e-3, 'machinability': 0.7},
                'CuW_LaB6': {'cost': 4.0, 'erosion': 0.89e-3, 'machinability': 0.6},
                'CuW_Sb': {'cost': 3.0, 'erosion': 1.37e-3, 'machinability': 0.65}
            },
            'insulators': {
                'Macor': {'cost': 3.0, 'erosion': 11.1, 'machinability': 0.8},  # g/m²
                'Alumina': {'cost': 5.0, 'erosion': 0.0, 'machinability': 0.1},
                'PEEK': {'cost': 1.5, 'erosion': 26.4, 'machinability': 0.9},
                'Polycarbonate': {'cost': 1.2, 'erosion': -10.8, 'machinability': 0.85}  # ganho de massa
            }
        }
        self._register_prolog()

    def _register_prolog(self):
        if self.prolog:
            self.prolog.assertz("plasma_railgun_substrate('Substrate 237 v2.0')")
            self.prolog.assertz("plasma_railgun_materials([Cu, CuW, CuW_LaB6, Macor, PEEK, Alumina])")
            self.prolog.assertz("plasma_railgun_instabilities([blow_by, restrike, erosion])")

    def set_wormgraph(self, wormgraph):
        self.wormgraph = wormgraph

    def simulate_shot(self, voltage: float = 7000.0,
                      capacitance: float = 58e-6,
                      gas_mass: float = 4.3e-6) -> Dict:
        """
        Simula um disparo completo do canhão.

        Args:
            voltage: tensão de carga (V)
            capacitance: capacitância (F)
            gas_mass: massa de gás (kg)
        """
        # Atualiza parâmetros
        self.params.voltage = voltage
        self.params.capacitance = capacitance
        self.params.gas_mass = gas_mass
        self.snowplow = SnowplowModel(self.params)
        self.instability = PlasmaInstabilityModel(self.params)

        # 1. Simula aceleração (snowplow)
        result = self.snowplow.simulate()
        if not result['success']:
            return {'status': 'error', 'message': result.get('message', 'Simulation failed')}

        # 2. Calcula instabilidades
        current_peak = result['peak_current']
        t_bb = self.instability.blow_by_time(current_peak)
        restrike_prob = self.instability.restrike_probability(current_peak, voltage)
        erosion_rate = self.instability.erosion_rate(self.params.electrode_material, current_peak)

        # 3. Cria jato de plasma (Coleman 2021)
        # Densidade eletrônica: ~2×10¹⁶ cm⁻³ (Coleman)
        n_e = 2.0e16 * 1e6  # m⁻³
        jet = PlasmaJet(
            velocity=result['exit_velocity'],
            density=n_e,
            temperature=1.4 * 11604.5,  # 1.4 eV -> K
            mass=result['exit_mass'],
            radius=self.params.outer_radius,
            length=0.20,  # ~20 cm (Coleman)
            ionization_fraction=0.96,  # Coleman
            electron_density=n_e,
            mach_number=14.0  # Coleman
        )

        # 4. Registra disparo
        shot = RailgunShot(
            shot_number=len(self.shots) + 1,
            voltage=voltage,
            current=result['current'],
            time=result['time'],
            jets=[jet],
            line_integrated_density=np.array([7.8e15 * 1e6]),  # m⁻²
            photodiode_intensity=np.array([1.0]),
            diagnostics={
                'exit_velocity': result['exit_velocity'],
                'exit_mass': result['exit_mass'],
                'exit_time': result['exit_time'],
                'peak_current': current_peak,
                'blow_by_time': t_bb,
                'restrike_probability': restrike_prob,
                'erosion_rate': erosion_rate
            },
            blow_by_time=t_bb,
            restrike_probability=restrike_prob
        )

        self.shots.append(shot)

        # Registra no WormGraph
        if self.wormgraph:
            self.wormgraph.commit({
                "event": "plasma_railgun_shot",
                "shot_number": shot.shot_number,
                "voltage": voltage,
                "peak_current": current_peak,
                "exit_velocity": result['exit_velocity'],
                "exit_mass": result['exit_mass'],
                "blow_by_time": t_bb,
                "restrike_prob": restrike_prob,
                "erosion_rate": erosion_rate
            })

        return {
            "status": "success",
            "shot_number": shot.shot_number,
            "parameters": {
                "voltage": voltage / 1000,
                "capacitance": capacitance * 1e6,
                "gas_mass": gas_mass * 1e6
            },
            "results": {
                "exit_velocity": result['exit_velocity'] / 1000,
                "exit_mass": result['exit_mass'] * 1e6,
                "peak_current": current_peak / 1000,
                "blow_by_time": t_bb,
                "restrike_probability": restrike_prob,
                "erosion_rate": erosion_rate * 1e3
            },
            "jet": {
                "velocity": jet.velocity / 1000,
                "density": jet.density / 1e6,
                "mass": jet.mass * 1e6,
                "temperature": jet.temperature,
                "mach": jet.mach_number,
                "ionization": jet.ionization_fraction
            }
        }

    def optimize_design(self, target_velocity: float = 20_000) -> Dict:
        """
        Otimiza parâmetros de projeto para atingir velocidade alvo.
        Baseado na metodologia de Coleman (2021).
        """
        best_params = None
        best_velocity = 0.0
        best_shot = None

        # Espaço de busca (Coleman)
        for V in np.linspace(5000, 11000, 7):
            for C in [50e-6, 58e-6, 70e-6]:
                for ratio in [1.5, 1.81, 2.0]:
                    # Atualiza parâmetros
                    test_params = CoaxialRailgunParams(
                        voltage=V,
                        capacitance=C,
                        electrode_ratio=ratio,
                        inner_radius=0.00915,
                        outer_radius=0.00915 * ratio
                    )
                    model = SnowplowModel(test_params)
                    result = model.simulate()

                    if result['success'] and result['exit_velocity'] > best_velocity:
                        best_velocity = result['exit_velocity']
                        best_params = {
                            'voltage': V,
                            'capacitance': C,
                            'electrode_ratio': ratio,
                            'exit_velocity': result['exit_velocity'],
                            'exit_mass': result['exit_mass'],
                            'peak_current': result['peak_current']
                        }
                        best_shot = result

        return {
            "status": "success",
            "best_velocity": best_velocity / 1000,
            "best_params": best_params,
            "target_velocity": target_velocity / 1000,
            "achieved": best_velocity >= target_velocity
        }

    def material_recommendation(self, current: float = 90e3) -> Dict:
        """
        Recomenda materiais para eletrodos e isoladores.
        Baseado em Rosenwasser & Stevenson (1986), Coleman (2021).
        """
        # Eletrodos
        electrode_candidates = []
        for name, props in self.materials_db['electrodes'].items():
            electrode_candidates.append({
                'material': name,
                'erosion_rate': props['erosion'] * 1e3,  # mg/C
                'cost_relative': props['cost'],
                'machinability': props['machinability'],
                'lifetime': 1.0 / props['erosion'] if props['erosion'] > 0 else float('inf'),
                'recommended': name == 'CuW'  # Coleman escolheu CuW
            })

        # Isoladores
        insulator_candidates = []
        for name, props in self.materials_db['insulators'].items():
            insulator_candidates.append({
                'material': name,
                'erosion_rate': props['erosion'],
                'cost_relative': props['cost'],
                'machinability': props['machinability'],
                'lifetime': 1.0 / props['erosion'] if props['erosion'] > 0 else float('inf'),
                'recommended': name == 'Macor'
            })

        return {
            "electrodes": sorted(electrode_candidates, key=lambda x: x['erosion_rate']),
            "insulators": sorted(insulator_candidates, key=lambda x: x['erosion_rate']),
            "current": current / 1000,
            "recommendations": {
                "electrode": "CuW",
                "insulator": "Macor",
                "reasoning": "CuW tem baixa erosão (1.24 mg/C) e boa usinabilidade. "
                            "Macor é cerâmica usinável com baixa erosão (11.1 g/m²) "
                            "e resistente a plasma."
            }
        }

# ============================================================================
# PREDICADOS PROLOG
# ============================================================================

PROLOG_PREDICATES_237 = """
%%% ========================================================================
%%% SUBSTRATO 237: PLASMA RAILGUN SIMULATOR
%%% ========================================================================

:- dynamic plasma_shot/6.
:- dynamic plasma_instability/4.
:- dynamic plasma_material/3.

plasma_register_shot(ID, Voltage, Current, Velocity, Density, Mass) :-
    assertz(plasma_shot(ID, Voltage, Current, Velocity, Density, Mass)),
    format('[Plasma] Shot ~w: V=~2f kV, v=~2f km/s~n', [ID, Voltage/1000, Velocity/1000]).

plasma_register_instability(ShotID, BlowBy, Restrike, Erosion) :-
    assertz(plasma_instability(ShotID, BlowBy, Restrike, Erosion)).

plasma_register_material(Name, Type, Erosion) :-
    assertz(plasma_material(Name, Type, Erosion)).

plasma_best_velocity(Velocity) :-
    findall(V, plasma_shot(_, _, _, V, _, _), Velocities),
    max_list(Velocities, Velocity).

plasma_shots_with_blowby(IDs) :-
    findall(ID, plasma_instability(ID, BlowBy, _, _), BlowBy < 10, IDs).

plasma_init :-
    retractall(plasma_shot(_, _, _, _, _, _)),
    retractall(plasma_instability(_, _, _, _)),
    retractall(plasma_material(_, _, _)),
    plasma_register_material('CuW', electrode, 1.24e-3),
    plasma_register_material('Macor', insulator, 11.1),
    plasma_register_material('PEEK', insulator, 26.4),
    format('[Plasma] Substrato 237 inicializado~n').
"""

# ============================================================================
# EXEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Inicializa substrato
    plasma = PlasmaRailgunSubstrate(None)

    # Simula um disparo (Coleman: 7 kV, 58 μF)
    shot = plasma.simulate_shot(7000.0)
    print(f"\n=== DISPARO {shot['shot_number']} ===")
    print(f"Velocidade: {shot['results']['exit_velocity']:.1f} km/s")
    print(f"Massa: {shot['results']['exit_mass']:.2f} mg")
    print(f"Corrente de pico: {shot['results']['peak_current']:.1f} kA")
    print(f"Blow-by: {shot['results']['blow_by_time']:.2f} μs")
    print(f"Restrike: {shot['results']['restrike_probability']:.1%}")

    # Otimização
    opt = plasma.optimize_design(target_velocity=30000)
    print(f"\n=== OTIMIZAÇÃO ===")
    print(f"Melhor velocidade: {opt['best_velocity']:.1f} km/s")
    print(f"Parâmetros: V={opt['best_params']['voltage']/1000:.1f} kV, C={opt['best_params']['capacitance']*1e6:.1f} μF")

    # Materiais
    mats = plasma.material_recommendation()
    print(f"\n=== MATERIAIS RECOMENDADOS ===")
    print(f"Eletrodo: {mats['recommendations']['electrode']}")
    print(f"Isolador: {mats['recommendations']['insulator']}")
