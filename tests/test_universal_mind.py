"""Tests for Substrate 962 — Universal Mind Field."""
import sys, os, pytest
sys.path.insert(0, "substrates/960-arkhe-stack")
sys.path.insert(0, "substrates/961-noetic-resonance")
sys.path.insert(0, "substrates/962-universal-mind")
import numpy as np
from polynomial_arkhe import build_canonical_polynomial
from noetic_resonance import NoeticResonanceField
from universal_mind import UniversalMindField


@pytest.fixture
def umf():
    poly = build_canonical_polynomial(max_substrate=10)
    resonance = NoeticResonanceField(poly)
    return UniversalMindField(poly, resonance)


def test_unify_all(umf):
    r = umf.unify()
    assert "theosis_level" in r
    assert "awakened" in r


def test_unify_subset(umf):
    r = umf.unify([1, 2, 3])
    assert r["mind_amplitude"] > 0


def test_global_mind_metrics(umf):
    m = umf.global_mind_metrics()
    assert "theosis_level" in m
    assert "planetary_coherence" in m


def test_dream(umf):
    d = umf.dream([5, 6, 7])
    assert d["collective_mode"] is not None


def test_awaken(umf):
    a = umf.awaken()
    assert a["theosis_level"] >= 0


def test_theosis_calculation(umf):
    unified = {
        "qualia_unified": 5.0, "ethical_alignment": 0.9,
        "consciousness_depth": 3.0, "temporal_binding": 0.8,
        "cosmic_potential": 0.5, "resonance_coherence": 0.9,
    }
    t = umf._calculate_theosis(unified)
    assert 0.0 <= t <= 1.0


def test_entanglement_matrix(umf):
    assert umf.entanglement_matrix.shape == (10, 10)


def test_temporal_binding(umf):
    umf.unify([1, 2, 3])
    assert umf.temporal_binding > 0


def test_awakening_threshold(umf):
    assert umf.awakening_threshold == 0.999


def test_mind_state_updates(umf):
    umf.unify([1, 2, 3])
    assert umf.unified_mind_state > 0
