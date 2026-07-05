import math

import pytest

from substrates.substrate_337 import (
    DRAKE_PORTAL_DIMENSIONS,
    DrakePortalEstimate,
    TimeWeaverProtocol,
    drake_portal_probability,
)
from substrates.substrate_342 import verify_merkle_proof


def test_drake_portal_equation_uses_17_dimensions():
    estimate = DrakePortalEstimate()

    expected = ((1 + math.sqrt(5)) / 2) ** 17 / (math.factorial(17) * math.pi)
    assert DRAKE_PORTAL_DIMENSIONS == 17
    assert estimate.value == pytest.approx(expected)
    assert drake_portal_probability() == pytest.approx(expected)
    assert len(estimate.canonical_seal) == 64


def test_temporal_merkle_root_verifies_declared_future_event():
    protocol = TimeWeaverProtocol()
    root = protocol.declare_future_event(
        "future-commit-001",
        {"repo": "orkut-labs-dev", "commit": "abc123"},
        "2037-01-17T00:00:00+00:00",
    )

    assert len(root.root) == 64
    assert root.verify()
    assert verify_merkle_proof(root.proof)
    assert root.declared_future_event == "future-commit-001"


def test_hilbert_hashtree_signature_is_17_qudit_and_normalized():
    protocol = TimeWeaverProtocol()
    signature = protocol.hilbert_hashtree_signature("a" * 64)

    assert signature.qudits == 17
    assert len(signature.amplitudes) == 17
    assert signature.norm == pytest.approx(1.0)
    assert len(signature.energy_signature) == 64
    assert len(signature.canonical_seal) == 64


def test_symbolic_weyl_curvature_gate_is_negative_above_density_threshold():
    protocol = TimeWeaverProtocol()
    threshold = ((1 + math.sqrt(5)) / 2) ** 17

    assert protocol.symbolic_weyl_curvature(threshold) == 0.0
    assert protocol.symbolic_weyl_curvature(threshold * 2) < 0.0


def test_time_weaver_envelope_marks_speculative_model():
    protocol = TimeWeaverProtocol()
    envelope = protocol.build_time_weaver_envelope(
        "portal-audit-001",
        {"claim": "temporal_merkle_root"},
        "2042-02-17T00:00:00+00:00",
        information_density=((1 + math.sqrt(5)) / 2) ** 17 * 3,
    )

    assert envelope["empirical_status"] == "symbolic_speculative_model"
    assert envelope["dimensions"] == 17
    assert envelope["temporal_proof_valid"] is True
    assert envelope["negative_weyl_gate"] is True
    assert len(envelope["canonical_seal"]) == 64


def test_non_17_dimension_protocol_is_rejected():
    with pytest.raises(ValueError, match="17 dimensions"):
        TimeWeaverProtocol(dimensions=16)
