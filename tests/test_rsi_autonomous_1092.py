import pytest
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rsi_autonomous_1092 import (
    Lean4CompilerSandbox, DockerSandbox, TemporalChainAnchor,
    RSIAutonomousCycle,
)


class TestLean4CompilerSandbox:

    def test_init(self):
        sbox = Lean4CompilerSandbox()
        assert sbox.lean_cmd == "lean"
        assert sbox.lake_cmd == "lake"
        assert sbox.timeout == 120
        assert sbox._compile_history == []

    def test_check_lean_available_returns_bool(self):
        sbox = Lean4CompilerSandbox()
        result = sbox._check_lean_available()
        assert isinstance(result, bool)

    def test_compile_returns_lean_not_found_when_unavailable(self, monkeypatch):
        sbox = Lean4CompilerSandbox(lean_cmd="nonexistent_lean_xyz")
        monkeypatch.setattr(sbox, '_check_lean_available', lambda: False)
        result = sbox.compile("theorem t : True := by trivial")
        assert result["status"] == "LEAN_NOT_FOUND"
        assert result["success"] is False
        assert "nao encontrado" in result["message"]

    def test_get_telemetry_format(self):
        sbox = Lean4CompilerSandbox()
        t = sbox.get_telemetry()
        assert t["module"] == "Lean4CompilerSandbox"
        assert t["version"] == "1.0.0"
        assert t["substrate"] == "1092.1"
        assert "seal" in t
        assert "lean_available" in t
        assert "total_compilations" in t
        assert "success_rate" in t
        assert isinstance(t["lean_available"], bool)

    def test_compile_history_increments(self):
        sbox = Lean4CompilerSandbox(lean_cmd="nonexistent_xyz")
        sbox.compile("test code")
        assert len(sbox._compile_history) == 1
        sbox.compile("more code")
        assert len(sbox._compile_history) == 2


class TestDockerSandbox:

    def test_init(self):
        ds = DockerSandbox()
        assert ds.image == "python:3.12-slim"
        assert ds.cpu_limit == 1.0
        assert ds.mem_limit == "512m"
        assert ds.timeout == 60
        assert ds.network_disabled is True

    def test_docker_available_returns_bool(self):
        ds = DockerSandbox()
        result = ds._docker_available()
        assert isinstance(result, bool)

    def test_execute_returns_docker_not_available_when_no_docker(self, monkeypatch):
        ds = DockerSandbox()
        monkeypatch.setattr(ds, '_docker_available', lambda: False)
        result = ds.execute("print('hello')", language="python")
        assert result["status"] == "DOCKER_NOT_AVAILABLE"
        assert result["success"] is False
        assert "Docker daemon nao acessivel" in result["message"]

    def test_get_telemetry_format(self):
        ds = DockerSandbox()
        t = ds.get_telemetry()
        assert t["module"] == "DockerSandbox"
        assert t["version"] == "1.0.0"
        assert t["substrate"] == "1092.2"
        assert "seal" in t
        assert "docker_available" in t
        assert "total_executions" in t
        assert "success_rate" in t
        assert isinstance(t["docker_available"], bool)

    def test_execution_history_increments(self):
        ds = DockerSandbox()
        ds.execute("test", "python")
        assert len(ds._execution_history) == 1


class TestTemporalChainAnchor:

    def test_init(self):
        tca = TemporalChainAnchor()
        assert tca.chain_id == "12120014"
        assert tca.rpc_url == "https://rpc.rbbchain.gov.br"
        assert tca.contract_address is None

    def test_compute_merkle_root_returns_hex_string(self):
        tca = TemporalChainAnchor()
        mr = tca._compute_merkle_root(b"test data")
        assert isinstance(mr, str)
        assert mr.startswith("0x")
        assert len(mr) == 66

    def test_compute_merkle_root_from_string(self):
        tca = TemporalChainAnchor()
        mr = tca._compute_merkle_root("hello")
        assert isinstance(mr, str)
        assert mr.startswith("0x")

    def test_anchor_returns_dict_with_expected_keys(self):
        tca = TemporalChainAnchor()
        r = tca.anchor("artifact_data", "SEAL-001", metadata={"key": "value"})
        assert r["status"] == "ANCHORED"
        assert "merkle_root" in r
        assert "tx_hash" in r
        assert "block_number" in r
        assert "chain_id" in r
        assert "seal" in r
        assert "zk_proof" in r
        assert "timestamp" in r
        assert "metadata" in r
        assert "anchor_time" in r
        assert r["seal"] == "SEAL-001"
        assert r["metadata"]["key"] == "value"

    def test_verify_returns_verified_true_for_known_seals(self):
        tca = TemporalChainAnchor()
        r = tca.anchor("data", "VERIFY-TEST")
        v = tca.verify(r["merkle_root"], "VERIFY-TEST")
        assert v["verified"] is True
        assert "tx_hash" in v
        assert "block_number" in v
        assert "timestamp" in v

    def test_verify_returns_false_for_unknown_seals(self):
        tca = TemporalChainAnchor()
        v = tca.verify("0xunknown", "UNKNOWN-SEAL")
        assert v["verified"] is False
        assert "nao encontrado" in v["message"]

    def test_get_telemetry_format(self):
        tca = TemporalChainAnchor()
        t = tca.get_telemetry()
        assert t["module"] == "TemporalChainAnchor"
        assert t["version"] == "1.0.0"
        assert t["substrate"] == "1092.3"
        assert "seal" in t
        assert "chain_id" in t
        assert "total_anchors" in t
        assert t["total_anchors"] == 0
        assert t["latest_anchor"] is None

    def test_telemetry_updates_after_anchor(self):
        tca = TemporalChainAnchor()
        tca.anchor("data", "SEAL")
        t = tca.get_telemetry()
        assert t["total_anchors"] == 1
        assert t["latest_anchor"] is not None


class TestRSIAutonomousCycle:

    def test_init_with_default_sandboxes(self):
        rsi = RSIAutonomousCycle()
        assert isinstance(rsi.lean, Lean4CompilerSandbox)
        assert isinstance(rsi.docker, DockerSandbox)
        assert isinstance(rsi.anchor, TemporalChainAnchor)
        assert rsi.cycle_count == 0

    def test_trigger_sindy_lean4_anchor_deploy_phases(self):
        rsi = RSIAutonomousCycle()
        result = rsi.trigger({"hidden_states": [
            np.random.randn(4) for _ in range(4)
        ]})
        assert result["cycle_id"] == "RSI-CYCLE-0001"
        assert "phases" in result
        assert "sindy" in result["phases"]
        assert "lean4" in result["phases"]
        assert "docker" in result["phases"]
        assert "anchor" in result["phases"]
        assert "deploy" in result["phases"]
        assert result["phases"]["sindy"]["status"] == "PLACEHOLDER"
        assert result["phases"]["lean4"]["status"] == "LEAN_NOT_FOUND"
        assert result["phases"]["docker"]["status"] == "DOCKER_NOT_AVAILABLE"
        assert result["phases"]["anchor"]["status"] == "ANCHORED"

    def test_cycle_count_increments(self):
        rsi = RSIAutonomousCycle()
        rsi.trigger({"hidden_states": [np.random.randn(4) for _ in range(4)]})
        assert rsi.cycle_count == 1
        rsi.trigger({"hidden_states": [np.random.randn(4) for _ in range(4)]})
        assert rsi.cycle_count == 2

    def test_new_substrate_id_increments(self):
        rsi = RSIAutonomousCycle()
        r1 = rsi.trigger({"hidden_states": [np.random.randn(4) for _ in range(4)]})
        r2 = rsi.trigger({"hidden_states": [np.random.randn(4) for _ in range(4)]})
        assert r2["new_substrate_id"] > r1["new_substrate_id"]

    def test_get_full_report_format(self):
        rsi = RSIAutonomousCycle()
        rsi.trigger({"hidden_states": [np.random.randn(4) for _ in range(4)]})
        report = rsi.get_full_report()
        assert report["module"] == "RSIAutonomousCycle"
        assert report["version"] == "1.0.0"
        assert report["substrate"] == "1092"
        assert "seal" in report
        assert report["cycles"] == 1
        assert "next_substrate_id" in report
        assert "lean_telemetry" in report
        assert "docker_telemetry" in report
        assert "anchor_telemetry" in report
        assert "cycle_history" in report
        assert len(report["cycle_history"]) == 1


class TestConstantsAndSeals:

    def test_seal_present_in_lean_telemetry(self):
        sbox = Lean4CompilerSandbox()
        t = sbox.get_telemetry()
        assert "LEAN4-SANDBOX-1092.1" in t["seal"]

    def test_seal_present_in_docker_telemetry(self):
        ds = DockerSandbox()
        t = ds.get_telemetry()
        assert "DOCKER-SANDBOX-1092.2" in t["seal"]

    def test_seal_present_in_anchor_telemetry(self):
        tca = TemporalChainAnchor()
        t = tca.get_telemetry()
        assert "TEMPORALCHAIN-ANCHOR-1092.3" in t["seal"]

    def test_seal_present_in_cycle_report(self):
        rsi = RSIAutonomousCycle()
        report = rsi.get_full_report()
        assert "RSI-AUTONOMO-1092" in report["seal"]


class TestEdgeCases:

    def test_anchor_without_metadata(self):
        tca = TemporalChainAnchor()
        r = tca.anchor("data", "NO-META")
        assert r["status"] == "ANCHORED"
        assert r["metadata"] == {}

    def test_anchor_deterministic_merkle_root(self):
        tca = TemporalChainAnchor()
        r1 = tca.anchor("same_data", "SEAL-A")
        r2 = tca.anchor("same_data", "SEAL-B")
        assert r1["merkle_root"] == r2["merkle_root"]

    def test_trigger_without_hidden_states(self):
        rsi = RSIAutonomousCycle()
        result = rsi.trigger({})
        assert result["phases"]["sindy"]["status"] == "PLACEHOLDER"
        assert "equation" in result["phases"]["sindy"]
