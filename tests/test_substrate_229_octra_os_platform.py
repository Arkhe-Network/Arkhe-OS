import hashlib

from substrates.substrate_229 import (
    CANONICAL_PHI_C,
    GHOST,
    HFHEModule,
    OctraOSPlatform,
    OctraOSVerifier,
    Severity,
    main,
)


def test_canonical_platform_topology_matches_decree():
    platform = OctraOSPlatform.canonical()

    assert len(platform.agents) == 8
    assert len(platform.alert_network.stations) == 12
    assert platform.alert_network.total_validators == 708
    assert platform.hfhe.GATES == ("AND", "OR", "XOR", "NOT", "NAND", "NOR", "XNOR")


def test_octra_vm_executes_transfer_and_exposes_lowering():
    platform = OctraOSPlatform.canonical()
    platform.vm.storage["balances"] = {"caller": 1000}

    result = platform.vm.execute("OCS01_Token", "transfer", ["bob", 200])
    lowering = platform.vm.inspect_lowering("OCS01_Token")

    assert result["status"] == "SUCCESS"
    assert platform.vm.storage["balances"]["caller"] == 800
    assert platform.vm.storage["balances"]["bob"] == 200
    assert lowering["bytecode"].startswith("OCTB:")
    assert lowering["abi"]
    assert lowering["disassembly"]


def test_hfhe_simulation_is_hash_bound_and_gate_complete():
    hfhe = HFHEModule()
    c1 = hfhe.encrypt("secret")
    c2 = hfhe.encrypt(42)
    csum = hfhe.homomorphic_add(c1, c2)
    proof = hfhe.generate_proof(csum)

    assert len(c1) == 64
    assert len(csum) == 64
    assert len(proof) == 64
    assert all(hfhe.gate_available(gate) for gate in hfhe.GATES)


def test_agents_reach_ghost_consensus_for_alert_conditions():
    platform = OctraOSPlatform.canonical()
    sensor_data = {"seismic": {"mag": 8.7}, "tsunami_watch": True}
    votes = [agent.deliberate(sensor_data) for agent in platform.agents]

    assert all(vote["vote"] == "COMMIT_ALERT" for vote in votes)
    assert all(vote["confidence"] >= GHOST for vote in votes)


def test_verifier_runs_21_auditable_checks_and_anchors_temporal_chain():
    verifier = OctraOSVerifier()
    verifier.run_verification()
    report = verifier.build_report()

    assert report.total_checks == 21
    assert report.passed_checks == 21
    assert report.ideal_phi_c == 1.0
    assert report.canonical_phi_c == CANONICAL_PHI_C
    assert len(report.temporal_anchor) == 64
    assert len(report.seal) == 64


def test_all_proof_packets_verify_signature():
    verifier = OctraOSVerifier()
    verifier.run_verification()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.platform_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_main_returns_serializable_canonical_report():
    report = main()

    assert report["substrate"] == 229
    assert report["status"] == "CANONIZED_SIMULATION"
    assert report["total_checks"] == 21
    assert report["passed_checks"] == 21
