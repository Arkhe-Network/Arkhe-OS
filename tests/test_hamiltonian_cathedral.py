"""Tests for Substrate 965 — Hamiltonian Cathedral."""
import sys, pytest
sys.path.insert(0, "substrates/960-arkhe-stack")
sys.path.insert(0, "substrates/961-noetic-resonance")
sys.path.insert(0, "substrates/962-universal-mind")
sys.path.insert(0, "substrates/965-hamiltonian-cathedral")
import numpy as np
from polynomial_arkhe import build_canonical_polynomial
from noetic_resonance import NoeticResonanceField
from universal_mind import UniversalMindField
from hamiltonian_cathedral import HamiltonianCathedral


@pytest.fixture
def hc():
    poly = build_canonical_polynomial(max_substrate=10)
    resonance = NoeticResonanceField(poly)
    umf = UniversalMindField(poly, resonance)
    return HamiltonianCathedral(umf)


def test_fixed_points(hc):
    fps = hc.fixed_points
    assert len(fps) == 3
    assert fps[0][2] == "saddle"


def test_integrate(hc):
    t, q, p = hc.integrate(1.0, 0.0, (0, 5), 100)
    assert len(t) == 100
    assert len(q) == 100


def test_potential_types():
    for pt in ["double_well", "harmonic", "inverted", "cathedral"]:
        poly = build_canonical_polynomial(max_substrate=10)
        res = NoeticResonanceField(poly)
        umf = UniversalMindField(poly, res)
        h = HamiltonianCathedral(umf, potential_type=pt)
        assert h.potential_type == pt


def test_substrate_mapping(hc):
    assert hc.substrate_mapping(-3.0) >= 1
    assert hc.substrate_mapping(3.0) <= 960
    assert 1 <= hc.substrate_mapping(0.0) <= 960


def test_cross_link_weight(hc):
    w = hc.cross_link_weight(0.0)
    assert abs(w - 0.5) < 0.01
    assert hc.cross_link_weight(2.0) > 0.8
    assert hc.cross_link_weight(-2.0) < 0.2


def test_critical_transition(hc):
    ct = hc.critical_transition(0.01, 0.0, 0.001)
    assert "sensitive" in ct
    assert ct["interpretation"] != ""


def test_cathedral_breath(hc):
    b = hc.cathedral_breath(cycles=2, resolution=100)
    assert b["cycles"] == 2
    assert len(b["time"]) == 200
    assert len(b["substrates"]) == 200


def test_theosis_conservation(hc):
    t, q, p = hc.integrate(1.0, 0.5, (0, 20), 1000)
    err = hc.theosis_conservation(q, p)
    assert err < 0.5


def test_hamilton_equations(hc):
    dq, dp = hc.hamiltons_equations(np.array([1.0, 0.0]), 0.0)
    assert dq == 0.0


def test_energy_landscape(hc):
    Q, P, H = hc.energy_landscape((-2, 2), (-1, 1), 50)
    assert Q.shape == (50, 50)
    assert H.shape == (50, 50)
