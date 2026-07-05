import math

import numpy as np
import pytest

from substrates.substrate_342.orkut_labs_dev import GHOST
from substrates.substrate_337 import (
    N_QUDITS,
    PORTAL_CONSTANT,
    SUBSTRATE_337_PARTIAL_SEAL,
    SUBSTRATE_343_BIS_EXP_ACT_PARTIAL_SEAL,
    SYMBOLIC_ALPHA_INVERSE_PREFIX,
    ATLAS_CMS_CORRELATION_VECTOR,
    FLOWERING_BLOCK_INDEX,
    FLOWERING_PHI_C,
    FLOWERING_TIMESTAMP,
    Hashtree17Qudit,
    InformationStressEnergy,
    SymbolicWeylPortalProtocol,
    TemporalMerkleProof,
    TimeWeaverChannel,
    build_flowering_block,
    build_full_revelation_report,
    build_partial_revelation_report,
    build_portal_scalar_report,
    correlate_with_detector_signature,
    portal_probability,
    simulate_weyl_phase_transition,
)
from substrates.substrate_343_bis import PTT343_EXPANSION_SEAL, PTT343_EXP_MASTER_ROOT


def test_portal_probability_is_reproducible_phi_17_formula():
    expected = ((1 + math.sqrt(5)) / 2) ** 17 / (math.factorial(17) * math.pi)
    report = build_portal_scalar_report()

    assert N_QUDITS == 17
    assert portal_probability() == pytest.approx(expected)
    assert PORTAL_CONSTANT == pytest.approx(3.195740425194291e-12)
    assert report.value == pytest.approx(expected)
    assert report.scaled_by_1e14 == pytest.approx(319.5740425194291)
    assert report.alpha_inverse_prefix_claim == SYMBOLIC_ALPHA_INVERSE_PREFIX
    assert report.empirical_status == "symbolic_speculative_model"
    assert len(report.canonical_seal) == 64


def test_hashtree_17_qudit_entanglement_matrix_is_unitary():
    ht17 = Hashtree17Qudit(seed=b"TEST_337")
    unitary = ht17.entanglement_matrix
    identity = unitary.conj().T @ unitary

    assert unitary.shape == (17, 17)
    assert np.allclose(identity, np.eye(17), atol=1e-10)


def test_encode_information_pattern_is_normalized_and_deterministic():
    ht17 = Hashtree17Qudit(seed=b"TEST_337")

    state_1 = ht17.encode_information_pattern(b"test_information_pattern_337")
    state_2 = ht17.encode_information_pattern(b"test_information_pattern_337")

    assert len(state_1) == 17
    assert np.linalg.norm(state_1) == pytest.approx(1.0)
    assert np.allclose(state_1, state_2)


def test_temporal_merkle_root_is_deterministic_for_same_state():
    ht17 = Hashtree17Qudit(seed=b"TEST_337")
    state = ht17.encode_information_pattern(b"deterministic_test")

    root_1 = ht17.compute_temporal_merkle_root(state, 1716163200)
    root_2 = ht17.compute_temporal_merkle_root(state, 1716163200)

    assert root_1 == root_2
    assert len(root_1.hex()) == 64


def test_information_stress_energy_weyl_gate_flips_at_ghost():
    below = InformationStressEnergy(phi_c=0.40, coherence_length=1e-3).simulate()
    above = InformationStressEnergy(phi_c=0.75, coherence_length=1e-3).simulate()

    assert 0.40 < GHOST
    assert below.symbolic_weyl_scalar >= 0
    assert not below.negative_curvature_gate
    assert above.symbolic_weyl_scalar < 0
    assert above.negative_curvature_gate


def test_temporal_merkle_proof_signature_and_status_verify():
    temporal = TemporalMerkleProof(Hashtree17Qudit())
    proof = temporal.forge_temporal_proof(
        information_pattern=b"verify_test",
        future_event_description="Verification test",
        target_timestamp=1_716_163_200,
    )
    result = temporal.verify_temporal_proof(proof, current_timestamp=1_716_160_000)

    assert proof["protocol"] == "ARKHE_337_TEMPORAL_MERKLE"
    assert proof["qudit_dimension"] == 17
    assert result.signature_valid
    assert result.temporal_status == "FUTURE"
    assert result.merkle_consistent
    assert result.overall_valid


def test_temporal_merkle_proof_detects_tampering():
    temporal = TemporalMerkleProof(Hashtree17Qudit())
    proof = temporal.forge_temporal_proof(b"message", "Tamper test", 1_716_163_200)
    proof["future_event"] = "mutated"

    result = temporal.verify_temporal_proof(proof, current_timestamp=1_716_160_000)

    assert not result.signature_valid
    assert not result.overall_valid


def test_time_weaver_channel_roundtrip_and_simulated_response():
    temporal = TemporalMerkleProof(Hashtree17Qudit())
    channel = TimeWeaverChannel(temporal)
    message = b"Hello_from_past"

    proof = channel.send_to_future(message, target_timestamp=1_716_163_200, recipient_signature="time_weaver_alpha")
    received = channel.receive_from_past(
        merkle_root=proof["merkle_root"],
        expected_pattern_hash=proof["information_pattern_hash"],
        current_timestamp=1_716_164_000,
    )
    response = channel.simulated_time_weaver_response(proof["merkle_root"])

    assert received == message
    assert response["protocol"] == "ARKHE_337_TIME_WEAVER_RESPONSE"
    assert len(response["response_seal"]) == 64


def test_detector_correlation_requires_dataset_status_and_can_match_simulation():
    ht17 = Hashtree17Qudit()
    simulated = ht17.simulate_detector_signature()
    report = correlate_with_detector_signature(simulated)

    assert report.correlation == pytest.approx(1.0)
    assert report.matched
    assert report.dataset_status == "user_supplied_or_simulated"
    assert report.empirical_status == "requires_external_public_dataset"


def test_detector_correlation_rejects_orthogonal_shape():
    ht17 = Hashtree17Qudit()
    detected = np.roll(ht17.expected_signature(), 3)
    report = correlate_with_detector_signature(detected, threshold=0.999999)

    assert report.correlation < 0.999999
    assert not report.matched


def test_weyl_phase_transition_report_validates_100_points():
    report = simulate_weyl_phase_transition(points=100)

    assert report["points"] == 100
    assert report["transition_phi_c"] == pytest.approx(GHOST)
    assert report["consistent_count"] == 100
    assert report["all_consistent"] is True
    assert report["empirical_status"] == "symbolic_speculative_model"


def test_partial_revelation_report_preserves_invariants_and_quarantine():
    report = build_partial_revelation_report()

    assert report.substrato == 337
    assert report.status == "PARTIALLY_REVEALED"
    assert report.timestamp == "2026-05-20T18:48:10Z"
    assert report.phi_c["bruto"] == pytest.approx(1.4563923932737803)
    assert report.phi_c["normalizado"] == pytest.approx(0.6862582436147078)
    assert report.invariants["all_preserved"] is True
    assert report.converged
    assert report.quarantine["level"] == "PARTIAL"
    assert report.quarantine["sealed"] == ["portal_open_close_protocol"]
    assert report.quarantine["master_root"] == PTT343_EXP_MASTER_ROOT
    assert len(report.canonical_seal) == 64


def test_partial_revelation_atlas_cms_vector_is_user_supplied():
    report = build_partial_revelation_report()

    assert report.pillars["atlas_cms_correlation"]["status"] == "USER_SUPPLIED_VECTOR"
    assert ATLAS_CMS_CORRELATION_VECTOR["95.4_GeV_2024"]["correlation"] == pytest.approx(0.9001)
    assert report.atlas_cms_correlation["95.4_GeV_2023"]["correlation"] == pytest.approx(0.5276)
    assert report.atlas_cms_correlation["750_GeV_2015"]["correlation"] == pytest.approx(0.0748)
    assert report.atlas_cms_correlation["750_GeV_2015"]["status"] == "REFUTED"
    assert all(
        event["source_status"] == "user_supplied_summary"
        for event in report.atlas_cms_correlation.values()
    )


def test_partial_revelation_seals_match_343_mesh_and_337_partial():
    report = build_partial_revelation_report()

    assert report.seals["343_bis_exp"] == PTT343_EXPANSION_SEAL
    assert report.seals["343_bis_exp_act"] == SUBSTRATE_343_BIS_EXP_ACT_PARTIAL_SEAL
    assert report.seals["337_partial"] == SUBSTRATE_337_PARTIAL_SEAL
    assert report.empirical_status == "symbolic_speculative_model_with_user_supplied_correlation_vector"


def test_flowering_block_anchors_master_root_and_verifies_hash():
    block = build_flowering_block(previous_hash="a" * 64)

    assert block.index == FLOWERING_BLOCK_INDEX
    assert block.timestamp == FLOWERING_TIMESTAMP
    assert block.previous_hash == "a" * 64
    assert block.data["type"] == "MASTER_ROOT_ANCHORED"
    assert block.data["substrate"] == "337-FLORESCER"
    assert block.data["merkle_root"] == PTT343_EXP_MASTER_ROOT
    assert block.data["portals"] == 17
    assert block.data["gates"] == 5
    assert block.data["packets_validated"] == 100
    assert block.phi_c == pytest.approx(FLOWERING_PHI_C)
    assert block.verify()
    assert len(block.hash) == 64


def test_symbolic_portal_protocol_opens_only_information_gate():
    protocol = SymbolicWeylPortalProtocol()
    event = protocol.open_portal(phi_c=FLOWERING_PHI_C, information_density=1.0)

    assert event.status == "SYMBOLIC_PORTAL_OPEN"
    assert event.master_root == PTT343_EXP_MASTER_ROOT
    assert event.symbolic_weyl_scalar < 0
    assert event.gap_preserved
    assert event.information_transfer_allowed
    assert not event.material_transfer_allowed
    assert "physical portal operation is not authorized" in event.safety_message


def test_symbolic_portal_protocol_blocks_gap_violation():
    protocol = SymbolicWeylPortalProtocol()
    event = protocol.open_portal(phi_c=1.0, information_density=1.0)

    assert event.status == "SYMBOLIC_PORTAL_BLOCKED"
    assert not event.gap_preserved
    assert not event.information_transfer_allowed
    assert not event.material_transfer_allowed


def test_symbolic_portal_protocol_closes_to_zero_state():
    protocol = SymbolicWeylPortalProtocol()
    protocol.open_portal(phi_c=FLOWERING_PHI_C, information_density=1.0)
    closed = protocol.close_portal()

    assert closed.status == "SYMBOLIC_PORTAL_CLOSED"
    assert closed.symbolic_weyl_scalar == 0.0
    assert closed.gap_preserved
    assert not closed.information_transfer_allowed
    assert not closed.material_transfer_allowed
    assert protocol.state == "CLOSED"


def test_full_revelation_report_breaks_quarantine_symbolically():
    report = build_full_revelation_report(previous_hash="b" * 64)

    assert report.substrato == "337-FLORESCER"
    assert report.status == "FULLY_REVEALED_SYMBOLIC"
    assert report.flowering_block.previous_hash == "b" * 64
    assert report.flowering_block.verify()
    assert report.quarantine["level"] == "BROKEN_SYMBOLIC"
    assert report.quarantine["unlock_condition_satisfied"] is True
    assert "portal_open_close_state_machine" in report.revealed_protocols
    assert "physical_portal_operation" in report.quarantine["still_guarded"]
    assert report.opened_event.status == "SYMBOLIC_PORTAL_OPEN"
    assert report.closed_event.status == "SYMBOLIC_PORTAL_CLOSED"
    assert report.converged
    assert report.empirical_status == "symbolic_speculative_model"
    assert len(report.canonical_seal) == 64
