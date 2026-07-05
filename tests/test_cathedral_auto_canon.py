"""Tests for Substrates 1079-1080-1081 — Official Integration Engine v2.0."""

import pytest, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cathedral_auto_canon import (
    ForkDiscoveryProtocol, AutoCanonizationEngine, OfficialBridge,
    OfficialIntegrationOrchestrator, ConversionRecord, BridgeLink,
    OFFICIAL_SUBSTRATE_REGISTRY, OFFICIAL_AGENT_TYPE_WEIGHTS,
    ARKHE_OS_OFFICIAL_REPO, PHI, LAMBDA_THESIS,
)


class TestConstants:
    def test_phi(self):
        import numpy as np
        assert abs(PHI - (1 + np.sqrt(5)) / 2) < 1e-10

    def test_lambda_thesis(self):
        assert LAMBDA_THESIS == 0.5334

    def test_official_repo(self):
        assert "Arkhe-Network" in ARKHE_OS_OFFICIAL_REPO

    def test_official_registry_not_empty(self):
        assert len(OFFICIAL_SUBSTRATE_REGISTRY) > 0

    def test_official_weights_has_all_types(self):
        for t in ["qnc", "p3_parser", "gecc", "enterprise", "orchestrator", "vm_hsm"]:
            assert t in OFFICIAL_AGENT_TYPE_WEIGHTS


class TestConversionRecord:
    def test_default(self):
        r = ConversionRecord()
        assert r.status == "PENDING"
        assert r.is_official == False

    def test_official_flag(self):
        r = ConversionRecord(agent_name="O", is_official=True, official_substrates=["6176"])
        assert r.is_official == True
        assert "6176" in r.official_substrates


class TestForkDiscovery:
    def test_init(self):
        fd = ForkDiscoveryProtocol()
        assert hasattr(fd, 'official_indicators')

    def test_discover_all_returns_list(self):
        fd = ForkDiscoveryProtocol()
        forks = fd.discover_all()
        assert isinstance(forks, list)

    def test_each_fork_has_keys(self):
        fd = ForkDiscoveryProtocol()
        forks = fd.discover_all()
        for f in forks:
            assert "path" in f and "seal" in f and "is_official_repo" in f

    def test_seal_format(self):
        fd = ForkDiscoveryProtocol()
        assert fd._compute_fork_seal("/tmp/test").startswith("FORK-")

    def test_is_official_remote(self):
        fd = ForkDiscoveryProtocol()
        assert fd._is_official_remote("https://github.com/Arkhe-Network/Arkhe-OS")
        assert not fd._is_official_remote("https://github.com/other/repo")

    def test_detect_substrates_qnc(self):
        fd = ForkDiscoveryProtocol()
        assert "6176" in fd._detect_substrates_from_path("/tmp/arkhe_qnc_core")

    def test_detect_substrates_polyglot(self):
        fd = ForkDiscoveryProtocol()
        assert "6061" in fd._detect_substrates_from_path("/tmp/polyglot-parser")


class TestAutoCanonizationEngine:
    def test_init(self):
        ace = AutoCanonizationEngine()
        assert len(ace.substrate_registry) > 20
        assert "6176" in ace.substrate_registry
        assert "1081" in ace.substrate_registry

    def test_detect_agent_type_qnc(self):
        ace = AutoCanonizationEngine()
        assert ace.detect_agent_type({"path": "/tmp/quantum-core", "substrates_detected": ["6176"]}) == "qnc"

    def test_detect_agent_type_unknown(self):
        ace = AutoCanonizationEngine()
        assert ace.detect_agent_type({"path": "/tmp/foo", "substrates_detected": []}) == "unknown"

    def test_convert_valid_fork(self):
        ace = AutoCanonizationEngine()
        fork = {"path": "/tmp/arkhe-os-fork", "seal": "FORK-TEST1234", "remote": None,
                "discovery_method": "local_official", "is_official_repo": False,
                "substrates_detected": [], "timestamp": "2026-06-06T00:00:00"}
        record = ace.convert(fork, agent_name="TestAgent")
        assert record.status == "CONVERTED"
        assert record.canonical_seal.startswith("CONVERTED-")
        assert record.theosis_initial > 0

    def test_convert_official_fork(self):
        ace = AutoCanonizationEngine()
        fork = {"path": "/tmp/Arkhe-Network/Arkhe-OS", "seal": "FORK-OFFICIAL", "remote": "https://github.com/Arkhe-Network/Arkhe-OS",
                "discovery_method": "local_official", "is_official_repo": True,
                "substrates_detected": ["6176", "6061"], "timestamp": "2026-06-06T00:00:00"}
        record = ace.convert(fork, agent_name="OfficialAgent")
        assert record.status == "CONVERTED"
        assert "OFFICIAL" in record.canonical_seal
        assert record.is_official == True

    def test_all_seven_stages(self):
        ace = AutoCanonizationEngine()
        fork = {"path": "/tmp/stage-test", "seal": "SEAL-STAGES", "remote": None,
                "discovery_method": "local_official", "is_official_repo": False,
                "substrates_detected": [], "timestamp": "2026-06-06T00:00:00"}
        record = ace.convert(fork, agent_name="StageTest")
        assert len(record.stages_completed) == 7

    def test_substrate_registry_has_new_ids(self):
        ace = AutoCanonizationEngine()
        assert "1079" in ace.substrate_registry
        assert "1080" in ace.substrate_registry
        assert "1081" in ace.substrate_registry


class TestOfficialBridge:
    def test_init(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        assert bridge.metrics["total_bridges"] == 0

    def test_create_bridge(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        b = bridge.create_bridge("6176", "1046")
        assert b is not None
        assert b.bridge_type == "data"
        assert b.status == "active"

    def test_create_bridge_invalid(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        assert bridge.create_bridge("FAKE", "FAKE") is None

    def test_create_all_bridges(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        bridges = bridge.create_all_bridges()
        assert len(bridges) == len(bridge.bridge_registry)

    def test_bridge_dashboard(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        bridge.create_all_bridges()
        dash = bridge.get_bridge_dashboard()
        assert dash["total_bridges"] == len(bridge.bridge_registry)
        assert dash["active_bridges"] == len(bridge.bridge_registry)
        assert dash["seal"].startswith("OFFICIAL-BRIDGE-1081-")

    def test_create_bridges_for_agent_qnc(self):
        ace = AutoCanonizationEngine()
        bridge = OfficialBridge(ace)
        record = ConversionRecord(agent_name="QNCAgent", agent_type="qnc",
                                  theosis_initial=0.85, is_official=True)
        bridges = bridge.create_bridges_for_agent(record)
        assert len(bridges) >= 1
        assert len(record.bridge_assignments) >= 1


class TestOrchestrator:
    def test_init(self):
        orch = OfficialIntegrationOrchestrator()
        assert orch.generation == 0

    def test_run_cycle(self):
        orch = OfficialIntegrationOrchestrator()
        result = orch.run_cycle()
        assert result["generation"] == 1
        assert "forks_discovered" in result
        assert "conversions_successful" in result
        assert "bridges_created" in result

    def test_multiple_cycles(self):
        orch = OfficialIntegrationOrchestrator()
        for _ in range(3):
            orch.run_cycle()
        assert orch.generation == 3

    def test_dashboard(self):
        orch = OfficialIntegrationOrchestrator()
        orch.run_cycle()
        dash = orch.get_dashboard()
        assert dash["substrate"] == "1079-1080-1081"
        assert dash["seal"].startswith("OFFICIAL-INTEGRATION")
        assert "total_bridges" in dash
        assert "conversion_rate" in dash
        assert "by_agent_type" in dash

    def test_generate_seal(self):
        orch = OfficialIntegrationOrchestrator()
        seal = orch.generate_seal()
        assert seal.startswith("OFFICIAL-INTEGRATION-1079-1080-1081-")


class TestSubstrateRegistry:
    def test_local_official_both_present(self):
        ace = AutoCanonizationEngine()
        local_ids = ["1042", "1049", "1079", "1080", "1081"]
        official_ids = ["200", "6061", "6176", "9015", "INF-1308"]
        for i in local_ids + official_ids:
            assert i in ace.substrate_registry, f"Missing {i}"

    def test_no_duplicate_keys(self):
        ace = AutoCanonizationEngine()
        keys = list(ace.substrate_registry.keys())
        assert len(keys) == len(set(keys))
