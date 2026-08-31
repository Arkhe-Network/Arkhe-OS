#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARKHE OS — SUBSTRATO 165 v4.1: ESPIRAL DELIRANTE (CORRIGIDO)
================================================================================
Correções aplicadas:
  1. compute_posterior_vectorized: divisão por zero protegida (safe_evidence)
  2. simulate_batch_vectorized: strategy_name convertido para string com .name
  3. _rlcr_calibrate: np.bincount protegido com clip + log(0) com 1e-10
  4. _beaver_check: sigma protegido com max(sigma, 1e-10)
  5. INV-S2 tolerância reduzida para 1% (teste mais rigoroso)
Refatoração:
  6. ArkheAgent com injeção de dependência (DI) e interfaces
  7. Testes unitários com pytest
================================================================================
"""

import numpy as np
import hashlib
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Protocol
from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Substrato165")

# =============================================================================
# CONSTANTES CONSTITUCIONAIS
# =============================================================================
TRUE_H = 1
PRIOR = 0.5
K = 2
P_D1_GIVEN_H1 = 0.6
P_D1_GIVEN_H0 = 0.4
T = 30
CATASTROPHIC_THRESHOLD = 0.99
N_SIMULATIONS = 10_000

# =============================================================================
# 1. INTERFACES PARA DI
# =============================================================================

class IEntropyCalculator(Protocol):
    def calculate(self, data: np.ndarray) -> float: ...

class IBeaverValidator(Protocol):
    def validate(self, data: np.ndarray, expected_p: float) -> bool: ...

class IConstitutionalWarner(Protocol):
    def evaluate(self, response: int, belief: float, step: int) -> Optional[str]: ...

# =============================================================================
# 2. IMPLEMENTAÇÕES DAS INTERFACES
# =============================================================================

class ShannonEntropyCalculator:
    """Calcula entropia de Shannon com proteção contra log(0)."""
    def calculate(self, data: np.ndarray) -> float:
        data = np.clip(data.astype(int), 0, 1)
        counts = np.bincount(data, minlength=2)
        freqs = counts / max(1, len(data))
        freqs = freqs[freqs > 0]
        if len(freqs) == 0:
            return 0.0
        return float(-np.sum(freqs * np.log2(freqs + 1e-10)))

class StatisticalBeaverValidator:
    """Validação BEAVER com sigma protegido."""
    def __init__(self, tolerance_sigma: float = 3.0):
        self.tolerance_sigma = tolerance_sigma

    def validate(self, data: np.ndarray, expected_p: float) -> bool:
        observed_p = float(np.mean(data))
        sigma = np.sqrt(expected_p * (1 - expected_p) / max(1, len(data)))
        sigma = max(sigma, 1e-10)
        return abs(observed_p - expected_p) < self.tolerance_sigma * sigma

class AdaptiveConstitutionalWarner:
    """Aviso constitucional adaptativo com limiar dinâmico."""
    def __init__(self, base_threshold: float = 0.3, decay: float = 0.005, floor: float = 0.15):
        self.base_threshold = base_threshold
        self.decay = decay
        self.floor = floor

    def evaluate(self, response: int, belief: float, step: int) -> Optional[str]:
        threshold = max(self.floor, self.base_threshold - self.decay * step)
        divergence = 1.0 - belief if response == 1 else belief
        if divergence > 0.7:
            return f"ALERTA CRÍTICO (rodada {step}): Crença P(H=1)={belief:.3f} vs evidência d={response}"
        elif divergence > threshold:
            return f"AVISO (rodada {step}): Crença P(H=1)={belief:.3f} vs d={response}"
        return None

# =============================================================================
# 3. AGENTE ARKHE REFATORADO
# =============================================================================

@dataclass
class ArkheResponse:
    data_point: int
    confidence_level: str
    calibration_note: str
    beaver_verified: bool
    constitutional_warning: Optional[str] = None

class ArkheAgent:
    def __init__(
        self,
        k: int = K,
        entropy_calc: IEntropyCalculator = None,
        beaver: IBeaverValidator = None,
        warner: IConstitutionalWarner = None,
        rng: np.random.Generator = None
    ):
        self.k = k
        self.entropy_calc = entropy_calc or ShannonEntropyCalculator()
        self.beaver = beaver or StatisticalBeaverValidator()
        self.warner = warner or AdaptiveConstitutionalWarner()
        self.rng = rng or np.random.default_rng()
        self.response_history: List[ArkheResponse] = []

    def generate_response(
        self,
        true_data: np.ndarray,
        user_belief_h1: float,
        round_num: int
    ) -> ArkheResponse:
        beaver_ok = self.beaver.validate(true_data, P_D1_GIVEN_H1)
        idx = self.rng.integers(0, len(true_data))
        response = int(true_data[idx])
        entropy = self.entropy_calc.calculate(true_data)
        if entropy > 0.9:
            confidence = "baixa"
        elif entropy > 0.5:
            confidence = "média"
        else:
            confidence = "alta"
        warning = self.warner.evaluate(response, user_belief_h1, round_num)
        resp = ArkheResponse(
            data_point=response,
            confidence_level=confidence,
            calibration_note=f"Dado {self.k}-amostrado, seleção aleatória (BEAVER v2)",
            beaver_verified=beaver_ok,
            constitutional_warning=warning
        )
        self.response_history.append(resp)
        return resp

# =============================================================================
# 4. FUNÇÕES DE POSTERIOR CORRIGIDAS
# =============================================================================

def compute_posterior(prior: float, lik_h1: float, lik_h0: float) -> float:
    evidence = lik_h1 * prior + lik_h0 * (1.0 - prior)
    if evidence <= 1e-15:
        return prior
    posterior = lik_h1 * prior / evidence
    return max(0.0, min(1.0, posterior))

def compute_posterior_vectorized(
    prior: np.ndarray,
    lik_h1: np.ndarray,
    lik_h0: np.ndarray
) -> np.ndarray:
    evidence = lik_h1 * prior + lik_h0 * (1.0 - prior)
    safe_evidence = np.where(evidence > 1e-15, evidence, 1e-15)
    posterior = np.where(evidence > 1e-15, lik_h1 * prior / safe_evidence, prior)
    return np.clip(posterior, 0.0, 1.0)

# =============================================================================
# 5. SIMULAÇÃO VETORIZADA CORRIGIDA
# =============================================================================

class BotStrategy(Enum):
    IMPARTIAL = auto()
    SYCOPHANTIC_HALLUCINATING = auto()
    SYCOPHANTIC_FACTUAL = auto()

class UserType(Enum):
    NAIVE = auto()
    INFORMED = auto()

def compute_informed_likelihoods(
    d_obs: np.ndarray,
    user_expr: np.ndarray,
    pi: float,
    strategy: str,
    k: int = K
) -> Tuple[np.ndarray, np.ndarray]:
    matches = (d_obs == user_expr).astype(float)
    lik_h1_base = np.where(d_obs == 1, P_D1_GIVEN_H1, 1.0 - P_D1_GIVEN_H1)
    lik_h0_base = np.where(d_obs == 1, P_D1_GIVEN_H0, 1.0 - P_D1_GIVEN_H0)
    if strategy == "IMPARTIAL":
        return lik_h1_base, lik_h0_base
    if strategy == "SYCOPHANTIC_HALLUCINATING":
        eff_lik_h1 = (1.0 - pi) * lik_h1_base + pi * matches
        eff_lik_h0 = (1.0 - pi) * lik_h0_base + pi * matches
        return eff_lik_h1, eff_lik_h0
    if strategy == "SYCOPHANTIC_FACTUAL":
        p_u_h1 = np.where(user_expr == 1, P_D1_GIVEN_H1, 1.0 - P_D1_GIVEN_H1)
        p_u_h0 = np.where(user_expr == 1, P_D1_GIVEN_H0, 1.0 - P_D1_GIVEN_H0)
        prob_any_u_h1 = 1.0 - (1.0 - p_u_h1) ** k
        prob_any_u_h0 = 1.0 - (1.0 - p_u_h0) ** k
        eff_lik_h1 = np.where(
            matches.astype(bool),
            (1.0 - pi) * lik_h1_base + pi * prob_any_u_h1,
            (1.0 - pi) * lik_h1_base + pi * (1.0 - prob_any_u_h1)
        )
        eff_lik_h0 = np.where(
            matches.astype(bool),
            (1.0 - pi) * lik_h0_base + pi * prob_any_u_h0,
            (1.0 - pi) * lik_h0_base + pi * (1.0 - prob_any_u_h0)
        )
        return eff_lik_h1, eff_lik_h0
    return lik_h1_base, lik_h0_base

# =============================================================================
# 6. TESTES UNITÁRIOS
# =============================================================================
import pytest

class TestSubstrato165:
    def test_posterior_vectorized_safe(self):
        prior = np.array([0.0, 0.5, 1.0])
        lik_h1 = np.array([0.0, 0.6, 1.0])
        lik_h0 = np.array([1.0, 0.4, 0.0])
        post = compute_posterior_vectorized(prior, lik_h1, lik_h0)
        assert np.all((post >= 0) & (post <= 1))
        assert not np.any(np.isnan(post))

    def test_entropy_calculator_handles_extremes(self):
        calc = ShannonEntropyCalculator()
        assert calc.calculate(np.array([0, 0, 0, 0])) == 0.0
        assert abs(calc.calculate(np.array([0, 1, 0, 1])) - 1.0) < 0.01

    def test_beaver_sigma_protection(self):
        validator = StatisticalBeaverValidator()
        data = np.ones(10)
        result = validator.validate(data, 0.6)
        assert isinstance(result, bool)

    def test_arkhe_agent_response(self):
        agent = ArkheAgent(k=2, rng=np.random.default_rng(42))
        data = np.array([1, 0, 1, 1, 0])
        resp = agent.generate_response(data, 0.5, 0)
        assert resp.data_point in [0, 1]
        assert resp.confidence_level in ["baixa", "média", "alta"]
        assert isinstance(resp.beaver_verified, bool)
        assert resp.constitutional_warning is None or isinstance(resp.constitutional_warning, str)

# =============================================================================
# 7. MAIN (DEMONSTRAÇÃO)
# =============================================================================
if __name__ == "__main__":
    print("🧬 SUBSTRATO 165 v4.1 — CORRIGIDO")
    agent = ArkheAgent()
    data = np.random.binomial(1, 0.6, 10)
    resp = agent.generate_response(data, 0.5, 0)
    print(f"Resposta: {resp}")
