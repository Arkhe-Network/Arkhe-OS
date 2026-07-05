import json

import pytest

from arkhe_global import GlobalRegionOrchestrator
from substrate_287 import (
    ArkheBidirectionalChannel,
    ArkheBidirectionalProtocol,
    TFQKDTemporalRouter,
    TemporalMeshOperator,
    TemporalMode,
    TimeSymmetricState,
    TimeSymmetryChannel,
)


def _protocol_with_transactions(count=5):
    protocol = ArkheBidirectionalProtocol(seed=42)
    for index in range(count):
        protocol.execute_handshake(
            {"H": 1.0 + index * 0.1, "Q": 1.0 + index * 0.2, "M": 0.45 + index * 0.04},
            {"H": 1.2 + index * 0.1, "Q": 1.4 + index * 0.1, "M": 0.50 + index * 0.03},
            t_past=index * 20,
            t_future=index * 20 + 50,
        )
    return protocol


def test_time_symmetric_state_normalizes_and_computes_amplitude():
    state = TimeSymmetricState([1 + 0j, 0 + 1j], [1 + 0j, 0 - 1j], 0.0)
    state.normalize()
    assert isinstance(state.bidirectional_amplitude(), complex)
    assert 0 <= state.transactional_probability() <= 1


def test_time_symmetric_state_weak_value():
    state = TimeSymmetricState([1 + 0j, 0 + 1j], [1 + 0j, 0 - 1j], 0.0)
    state.normalize()
    operator = [[1 + 0j, 0j], [0j, 1 + 0j]]
    assert isinstance(state.weak_value(operator), complex)


def test_time_symmetric_state_dimension_guard():
    with pytest.raises(ValueError):
        TimeSymmetricState([1 + 0j], [1 + 0j, 2 + 0j], 0.0)


def test_channel_establishes_offer_confirmation_and_transaction():
    channel = ArkheBidirectionalChannel(seed=42)
    tx = channel.establish_transaction({"H": 1, "Q": 1, "M": 0.5}, {"H": 1.1, "Q": 1.2, "M": 0.6}, 0, 50)
    assert tx.mode == TemporalMode.TRANSACTION
    assert tx.verify_transaction()
    assert len(channel.messages) == 3
    assert len(channel.transactions) == 1


def test_channel_queries_past_and_future_boundaries():
    channel = ArkheBidirectionalChannel(seed=42)
    channel.establish_transaction({"H": 1, "Q": 1, "M": 0.5}, {"H": 1.1, "Q": 1.2, "M": 0.6}, 0, 50)
    assert channel.query_past_from_future(60, 0) is not None
    assert channel.query_future_from_past(0, 50) is not None


def test_channel_metrics_are_complete():
    channel = ArkheBidirectionalChannel(seed=42)
    channel.establish_transaction({"H": 1, "Q": 1, "M": 0.5}, {"H": 1.1, "Q": 1.2, "M": 0.6}, 0, 50)
    metrics = channel.channel_metrics()
    assert metrics["offers"] == 1
    assert metrics["confirmations"] == 1
    assert metrics["transactions"] == 1
    assert metrics["transaction_success_rate"] == 1.0
    assert metrics["bidirectional_ratio"] > 0


def test_message_ids_are_unique_and_serializable():
    protocol = _protocol_with_transactions()
    ids = [message.message_id for message in protocol.channel.messages]
    assert len(ids) == len(set(ids))
    assert isinstance(json.dumps(protocol.channel.transactions[0].to_dict()), str)


def test_protocol_report_preserves_invariants():
    protocol = _protocol_with_transactions()
    report = protocol.generate_protocol_report()
    assert report["constitutional_invariants"]["ghost"]
    assert report["constitutional_invariants"]["loopseal"]
    assert report["constitutional_invariants"]["gap"]
    assert report["constitutional_invariants"]["constitutional"]
    assert report["phi_c"] >= 0.95


def test_protocol_report_has_temporal_seal_and_no_loops():
    protocol = _protocol_with_transactions()
    report = protocol.generate_protocol_report()
    assert report["n_loops"] == 0
    assert len(report["temporal_seal"]) == 64
    assert isinstance(json.dumps(report), str)


def test_retrocausal_intervention_creates_new_transaction():
    protocol = _protocol_with_transactions()
    tx_count = len(protocol.channel.transactions)
    intervention = protocol.retrocausal_intervention(0, {"H": 2.0, "Q": 3.0, "M": 0.4})
    assert intervention is not None
    assert len(protocol.channel.transactions) == tx_count + 1
    assert intervention.content_past["H"] == 2.0


def test_retrocausal_intervention_returns_none_for_missing_target():
    protocol = _protocol_with_transactions()
    assert protocol.retrocausal_intervention(999, {"H": 2.0}) is None


def test_formal_certificate_verifies_substrate_287():
    protocol = _protocol_with_transactions()
    certificate = protocol.formal_certificate()
    assert certificate["substrate_id"] == "287"
    assert certificate["verified"]
    assert len(certificate["temporal_seal"]) == 64


def test_temporal_fidelity_is_bounded():
    protocol = _protocol_with_transactions()
    assert all(0 <= tx.temporal_fidelity() <= 1 for tx in protocol.channel.transactions)


def test_compact_time_symmetry_channel_session():
    channel = TimeSymmetryChannel(seed=42)
    messages = channel.run_bidirectional_session(5)
    assert len(messages) == 5
    assert all(message.consistent for message in messages)
    assert len(channel.temporal_seals) == 10


def test_temporal_mesh_operator_report():
    operator = TemporalMeshOperator(seed=42)
    report = operator.activate_full_temporal_mesh()
    assert report["substrate"] == "287"
    assert report["messages_sent"] == 5
    assert report["paradox_status"]["paradox_free"]
    assert report["invariants"]["constitutional"]
    assert report["phi_c"] == 1.0
    assert len(report["canonical_seal"]) == 64


def test_temporal_mesh_operator_custom_message_count():
    operator = TemporalMeshOperator(seed=7)
    report = operator.activate_full_temporal_mesh(num_messages=3)
    assert report["messages_sent"] == 3
    assert len(report["temporal_seals"]) == 6


@pytest.mark.asyncio
async def test_tfqkd_router_classifies_ready_links():
    orchestrator = GlobalRegionOrchestrator()
    router = TFQKDTemporalRouter(orchestrator, seed=42)
    assert router.classify_link("us-east-1", "eu-west-1") == "ready"


@pytest.mark.asyncio
async def test_tfqkd_router_classifies_planned_links():
    orchestrator = GlobalRegionOrchestrator()
    router = TFQKDTemporalRouter(orchestrator, seed=42)
    assert router.classify_link("af-south-1", "eu-west-1") == "planned_or_pilot"
    assert router.classify_link("ap-south-1", "ap-northeast-1") == "planned_or_pilot"


@pytest.mark.asyncio
async def test_route_transaction_anchors_event():
    protocol = _protocol_with_transactions(1)
    orchestrator = GlobalRegionOrchestrator()
    router = TFQKDTemporalRouter(orchestrator, seed=42)
    route = await router.route_transaction(protocol.channel.transactions[0], "us-east-1", "eu-west-1")
    assert route.routing_mode == "tf_qkd_direct_temporal_anchor"
    assert route.anchor_seal
    assert len(route.canonical_seal) == 64
    assert orchestrator.anchoring.pending_anchors["us-east-1"]


@pytest.mark.asyncio
async def test_route_transaction_for_planned_backbone():
    protocol = _protocol_with_transactions(1)
    orchestrator = GlobalRegionOrchestrator()
    router = TFQKDTemporalRouter(orchestrator, seed=42)
    route = await router.route_transaction(protocol.channel.transactions[0], "me-south-1", "eu-west-1")
    assert route.routing_mode == "tf_qkd_planned_backbone_overlay"
    assert route.tf_qkd_state == "planned_or_pilot"
    assert route.retroactive


@pytest.mark.asyncio
async def test_anchor_mesh_routes_all_planned_regions():
    protocol = _protocol_with_transactions(5)
    orchestrator = GlobalRegionOrchestrator()
    router = TFQKDTemporalRouter(orchestrator, seed=42)
    report = await router.anchor_mesh(protocol.channel.transactions)
    assert report["regions_total"] == 8
    assert set(report["planned_backbone_regions"]) == {"af-south-1", "me-south-1", "ap-south-1"}
    assert report["planned_backbone_routes"] >= 3
    assert report["route_count"] >= len(protocol.channel.transactions) + 3
    assert len(report["canonical_seal"]) == 64


@pytest.mark.asyncio
async def test_anchor_mesh_reaches_global_consensus():
    protocol = _protocol_with_transactions(5)
    router = TFQKDTemporalRouter(GlobalRegionOrchestrator(), seed=42)
    report = await router.anchor_mesh(protocol.channel.transactions)
    assert report["consensus_reached"]
    assert report["global_phi_c"] >= 0.9


@pytest.mark.asyncio
async def test_anchor_mesh_report_is_json_serializable():
    protocol = _protocol_with_transactions(5)
    router = TFQKDTemporalRouter(GlobalRegionOrchestrator(), seed=42)
    report = await router.anchor_mesh(protocol.channel.transactions)
    assert isinstance(json.dumps(report), str)


@pytest.mark.asyncio
async def test_anchor_mesh_rejects_empty_transactions():
    router = TFQKDTemporalRouter(GlobalRegionOrchestrator(), seed=42)
    with pytest.raises(ValueError):
        await router.anchor_mesh([])


@pytest.mark.asyncio
async def test_region_planner_matches_substrate_287_policy():
    orchestrator = GlobalRegionOrchestrator()
    plan = orchestrator.tf_qkd_planner.generate_deployment_plan()
    assert plan["planned_region_count"] == 3
    assert {item["region_id"] for item in plan["regions"]} == {"af-south-1", "me-south-1", "ap-south-1"}


def test_protocol_final_state_can_feed_formal_verifier():
    protocol = _protocol_with_transactions()
    report = protocol.generate_protocol_report()
    assert report["final_state"]["H"] >= 0.577553
    assert report["final_state"]["Q"] >= 0.349066
    assert report["final_state"]["M"] < 1.0


def test_channel_is_deterministic_for_same_seed():
    a = ArkheBidirectionalChannel(seed=10)
    b = ArkheBidirectionalChannel(seed=10)
    tx_a = a.establish_transaction({"H": 1, "Q": 1, "M": 0.5}, {"H": 1.2, "Q": 1.3, "M": 0.6}, 0, 1)
    tx_b = b.establish_transaction({"H": 1, "Q": 1, "M": 0.5}, {"H": 1.2, "Q": 1.3, "M": 0.6}, 0, 1)
    assert tx_a.message_id == tx_b.message_id
    assert tx_a.transaction_strength == tx_b.transaction_strength


def test_temporal_loop_detector_flags_manual_bad_transaction():
    protocol = _protocol_with_transactions(1)
    protocol.channel.transactions[0].t_transaction = -1
    loops = protocol.temporal_loop_detection()
    assert len(loops) == 1
    assert loops[0]["type"] == "temporal_loop"


def test_transaction_success_rate_never_exceeds_one():
    protocol = _protocol_with_transactions(5)
    assert protocol.generate_protocol_report()["metrics"]["transaction_success_rate"] <= 1.0


def test_all_protocol_messages_have_valid_timestamps():
    protocol = _protocol_with_transactions()
    assert all(message.t_emit >= 0 for message in protocol.channel.messages)
    assert all(message.t_absorb >= message.t_emit for message in protocol.channel.messages)
