import math

import pytest

from substrates.substrate_343_bis import (
    CANONICAL_PORTAL_ENERGY_TEV,
    PORTAL_DIMENSIONS,
    PORTAL_FRACTION,
    SeventeenQuditPortal,
    build_ptt343_canonical_report,
    canonical_ptt343_proof,
    canonical_ptt343_vector,
    portal_fraction,
    verify_ptt343_merkle_proof,
)
from substrates.substrate_342 import compute_merkle_root, verify_merkle_proof


def test_portal_fraction_matches_phi_17_formula():
    phi = (1 + math.sqrt(5)) / 2
    expected = phi**17 / (math.factorial(17) * math.pi)

    assert PORTAL_DIMENSIONS == 17
    assert portal_fraction() == pytest.approx(expected)
    assert PORTAL_FRACTION == pytest.approx(3.195740425194291e-12)
    assert PORTAL_FRACTION < 0.9999


def test_portal_builds_16_data_leaves_plus_temporal_parity_qudit():
    portal = SeventeenQuditPortal()
    leaves = portal.build_leaves({"intent": "temporal-merkle-root"})

    assert len(leaves) == 17
    assert len(set(leaves)) == 17
    assert portal.qecc_distance(leaves) == 5
    assert compute_merkle_root(leaves)


def test_17th_parity_qudit_has_valid_merkle_proof():
    portal = SeventeenQuditPortal()
    demonstration = portal.demonstrate(
        {"repo": "orkut-labs-dev", "commit": "future-preimage"},
        "2045-01-17T00:00:00+00:00",
    )

    assert demonstration.parity_proof.leaf_index == 16
    assert demonstration.parity_proof.leaf == demonstration.temporal_parity_leaf
    assert verify_merkle_proof(demonstration.parity_proof)
    assert demonstration.verify()
    assert len(demonstration.canonical_seal) == 64


def test_triple_condition_requires_symbolic_2_3_tev_alignment():
    portal = SeventeenQuditPortal()

    aligned = portal.demonstrate({"x": 1}, "2045-01-17T00:00:00+00:00", observed_energy_tev=2.3)
    misaligned = portal.demonstrate({"x": 1}, "2045-01-17T00:00:00+00:00", observed_energy_tev=2.8)

    assert CANONICAL_PORTAL_ENERGY_TEV == 2.3
    assert aligned.invariant_report.satisfied
    assert not misaligned.invariant_report.satisfied
    assert not misaligned.verify()


def test_canonical_envelope_marks_speculative_status():
    portal = SeventeenQuditPortal()
    envelope = portal.build_canonical_envelope(
        {"arkhe": "343-bis", "token": "orcid:0009-0005-2697-4668"},
        "2045-01-17T00:00:00+00:00",
    )

    assert envelope["empirical_status"] == "symbolic_speculative_model"
    assert envelope["dimensions"] == 17
    assert envelope["data_qudits"] == 16
    assert envelope["temporal_parity_qudit"] == 1
    assert envelope["proof_valid"] is True
    assert len(envelope["canonical_seal"]) == 64
    assert len(envelope["envelope_seal"]) == 64


def test_ptt343_reference_vector_matches_decree():
    vector = canonical_ptt343_vector()

    assert vector["protocol"] == "PTT-343"
    assert vector["substrato"] == "343-BIS"
    assert vector["simulator_seed"] == 343343
    assert vector["qudit_count"] == 17
    assert vector["qudit_dimension"] == 17
    assert vector["qudit_outcomes"] == [15, 13, 14, 8, 11, 11, 2, 6, 10, 11, 1, 11, 10, 5, 12, 6, 1]
    assert vector["constant_phi_portal"] == pytest.approx(PORTAL_FRACTION)
    assert vector["merkle_root"] == "7a56573dd974a18bf8771d8b7ad5f318e72d71eef0dcf5294d4c09c5a2c931f5"


def test_ptt343_reference_merkle_proof_verifies_qudit_zero():
    proof = canonical_ptt343_proof()

    assert proof.leaf_index == 0
    assert proof.leaf == "b5f9d572d41a52bf00b96c4786896fa1728443cd9b5e87a295a11db230e833de"
    assert proof.root == "7a56573dd974a18bf8771d8b7ad5f318e72d71eef0dcf5294d4c09c5a2c931f5"
    assert len(proof.proof) == 5
    assert verify_ptt343_merkle_proof()


def test_ptt343_canonical_report_converges_all_12_checks():
    report = build_ptt343_canonical_report()

    assert report.proof_valid
    assert report.logical_tests == 12
    assert report.logical_tests_passed == 12
    assert report.converged
    assert len(report.canonical_seal) == 64
