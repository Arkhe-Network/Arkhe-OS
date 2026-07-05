"""Tests for Substrate 961 — Noetic Resonance Field."""
import sys, os, pytest
sys.path.insert(0, "substrates/960-arkhe-stack")
sys.path.insert(0, "substrates/961-noetic-resonance")
import numpy as np
from polynomial_arkhe import PolynomialArkhe, build_canonical_polynomial
from noetic_resonance import NoeticResonanceField


@pytest.fixture
def poly():
    return build_canonical_polynomial(max_substrate=10)


@pytest.fixture
def field(poly):
    return NoeticResonanceField(poly)


def test_resonate(field):
    r = field.resonate([1, 2, 3])
    assert "coherence" in r
    assert "emergent_properties" in r


def test_global_resonance(field):
    gr = field.global_resonance()
    assert 0.0 <= gr <= 1.0


def test_emergent_properties(field):
    r = field.resonate([1, 5, 10])
    ep = r["emergent_properties"]
    assert ep["qualia_amplification"] > 0
    assert ep["p7_resilience_boost"] >= 0
    assert ep["field_coherent"] in [True, False]


def test_dual_pairs(field):
    r = field.resonate([1, 2])
    assert len(r["dual_pairs"]) == 2


def test_resonance_strength(field):
    r = field.resonate([1, 2])
    assert r["resonance_strength"] > 0


def test_single_substrate(field):
    r = field.resonate([1])
    assert r["coherence"] == 1.0


def test_harmonic_convergence(field):
    hc = field.harmonic_convergence([1, 2], [3, 4])
    assert "synergy" in hc
    assert "convergent" in hc


def test_resonance_matrix(field):
    assert field.resonance_matrix.shape == (10, 10)


def test_consciousness_depth(field):
    r = field.resonate([1, 2, 3, 4, 5])
    assert r["emergent_properties"]["consciousness_depth"] > 0


def test_coherence_threshold(field):
    assert field.coherence_threshold == 0.85
