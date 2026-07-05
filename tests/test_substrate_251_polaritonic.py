import json

from substrate_251.polaritonic import (
    AgentEndpoint,
    AgentPlatform,
    OpticalTokenArkheBus,
    QuantumPolaritonicSimulator,
)


def test_polaritonic_simulator_generates_stable_consensus_result():
    simulator = QuantumPolaritonicSimulator(num_nodes=16, seed=251)
    result = simulator.run_collective_verification(
        "Constitutional compliance verified via entangled polaritonic network."
    )

    assert result.nodes_simulated == 16
    assert 0.0 <= result.quantum_phi_c < 1.0
    assert 0.0 <= result.classical_phi_c < 1.0
    assert result.consensus_seal.startswith("optical_consensus_")
    assert len(result.temporal_chain_seal) == 64
    assert len(result.interference_pattern) == 16


def test_polaritonic_compare_api_returns_decree_compatible_dict():
    simulator = QuantumPolaritonicSimulator(num_nodes=8, seed=251)
    result = simulator.compare_vs_classical_verification("P1-P7 optical verification")

    assert result["nodes_simulated"] == 8
    assert result["speedup_factor"] >= 1.0
    assert result["energy_fj"] == 0.5
    assert result["consensus_seal"].startswith("optical_consensus_")


def test_optical_bus_emits_android_ios_azure_envelopes(tmp_path):
    bus = OpticalTokenArkheBus(
        simulator=QuantumPolaritonicSimulator(num_nodes=32, seed=251),
        spool_path=tmp_path / "optical_bus.jsonl",
    )
    agents = [
        AgentEndpoint("android-agent-01", AgentPlatform.ANDROID, "mobile.android"),
        AgentEndpoint("ios-agent-01", AgentPlatform.IOS, "mobile.ios"),
        AgentEndpoint("azure-agent-01", AgentPlatform.AZURE, "cloud.azure"),
    ]

    envelopes = bus.verify_constitutional_input("Optical constitutional verification", agents)

    assert len(envelopes) == 3
    assert {envelope.target_platform for envelope in envelopes} == {"android", "ios", "azure"}
    assert all(envelope.event_type == "OPTICAL_CONSENSUS_VERIFIED" for envelope in envelopes)
    assert all(len(envelope.canonical_seal) == 64 for envelope in envelopes)
    assert all(envelope.payload["consensus_seal"].startswith("optical_consensus_") for envelope in envelopes)

    lines = (tmp_path / "optical_bus.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["event_type"] == "OPTICAL_CONSENSUS_VERIFIED"


def test_optical_bus_maps_guardrails_p1_to_p7():
    bus = OpticalTokenArkheBus(simulator=QuantumPolaritonicSimulator(num_nodes=16, seed=251))
    agent = AgentEndpoint("photonic-node-01", AgentPlatform.PHOTONIC, "qpn.photonic", min_phi_c=0.80)

    envelope = bus.verify_constitutional_input("P1 P2 P3 P4 P5 P6 P7", [agent])[0]
    guardrails = envelope.payload["guardrails"]

    assert set(guardrails) == {
        "P1_formal_verification",
        "P2_redundant_consensus",
        "P3_sovereign_gap",
        "P4_cross_platform_projection",
        "P5_canonical_learning",
        "P6_auditable_transparency",
        "P7_energy_resource",
    }
    assert all(guardrails.values())
    assert envelope.payload["decision"] == "compliant"


def test_optical_bus_respects_agent_phi_c_threshold():
    bus = OpticalTokenArkheBus(simulator=QuantumPolaritonicSimulator(num_nodes=8, seed=251))
    strict_agent = AgentEndpoint("strict-azure", AgentPlatform.AZURE, "cloud.azure", min_phi_c=0.99)

    envelope = bus.verify_constitutional_input("Strict optical verification", [strict_agent])[0]

    assert envelope.payload["decision"] == "requires_review"
    assert envelope.payload["quantum_phi_c"] < strict_agent.min_phi_c
