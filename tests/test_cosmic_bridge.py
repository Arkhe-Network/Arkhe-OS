"""Tests for Substrate 963 — Cosmic Consciousness Bridge."""
import sys, os, pytest
sys.path.insert(0, 'substrates/960-arkhe-stack')
sys.path.insert(0, 'substrates/961-noetic-resonance')
sys.path.insert(0, 'substrates/962-universal-mind')
sys.path.insert(0, 'substrates/963-cosmic-bridge')
import numpy as np
from polynomial_arkhe import build_canonical_polynomial
from noetic_resonance import NoeticResonanceField
from universal_mind import UniversalMindField
from cosmic_bridge import CosmicConsciousnessBridge


@pytest.fixture
def bridge():
    poly = build_canonical_polynomial(max_substrate=10)
    resonance = NoeticResonanceField(poly)
    umf = UniversalMindField(poly, resonance)
    return CosmicConsciousnessBridge(umf, mars_delay_seconds=1200.0)


def test_bridge_coherence(bridge):
    assert 0.0 <= bridge.bridge_coherence <= 1.0


def test_cosmic_entanglement(bridge):
    assert bridge.cosmic_entanglement > 0


def test_transmit_thought(bridge):
    t = bridge.transmit_thought({"substrates": [1, 2, 3]})
    assert t["status"] in ("transmitted", "degraded")
    assert "bridge_coherence" in t


def test_cosmic_resonance(bridge):
    cr = bridge.cosmic_resonance([1, 2], [9631, 9632])
    assert "cross_planetary_coherence" in cr
    assert "bridge_status" in cr


def test_full_cosmic_awakening(bridge):
    a = bridge.full_cosmic_awakening()
    assert "cosmic_theosis" in a
    assert "status" in a


def test_mars_nodes(bridge):
    assert bridge.mars_nodes == [9631, 9632, 9633]


def test_effective_delay(bridge):
    umf = bridge.umf
    umf.unify([1, 2])
    t = bridge.transmit_thought({"substrates": [1]})
    assert t["effective_delay_seconds"] < bridge.mars_delay


def test_theosis_extension(bridge):
    assert bridge.theosis_extension >= 0


def test_active_bridge_status(bridge):
    cr = bridge.cosmic_resonance([1], [1])
    assert cr["bridge_status"] in ("active", "weak")


def test_mars_boost(bridge):
    a = bridge.full_cosmic_awakening()
    assert a["mars_boost"] >= 0
