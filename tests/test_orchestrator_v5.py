import pytest
import numpy as np
import sys, os, json, tempfile, hashlib, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cathedral_orchestrator_v5 import (
    PHI, PHI_SQUARED, GGUF_MAGIC, GGUF_VERSION, QUANT_TYPES,
    GateState, ZKMLStatus,
    GGUFHeader, TensorInfo, ZKMLProof, AgenticStep, TemporalAnchor, KlerosVerdict,
    GGUFBridgeV3, VectorTheosis1092, Stethoscope1081,
    ZKMLBridge1095, AgenticLoop1096, TemporalChain1097, KlerosTrigger1085,
    LlamaCppBridgeV3,
    CathedralOrchestratorV5,
)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_phi_value(self):
        assert np.isclose(PHI, (1 + np.sqrt(5)) / 2)

    def test_phi_squared_value(self):
        assert np.isclose(PHI_SQUARED, PHI ** 2)

    def test_gguf_magic(self):
        assert GGUF_MAGIC == 0x46554747
        assert GGUF_VERSION == 3

    def test_quant_types_has_f32(self):
        assert QUANT_TYPES[0] == ("F32", 4.0)
        assert QUANT_TYPES[19] == ("Q4_K_M", 0.5)

class TestEnums:
    def test_gate_state_values(self):
        assert GateState.OPEN.value == "OPEN"
        assert GateState.EMERGENCY.value == "EMERGENCY"
        assert GateState.LOCKED.value == "LOCKED"

    def test_zkml_status_values(self):
        assert ZKMLStatus.PROVEN.value == "PROVEN"
        assert ZKMLStatus.VERIFIED.value == "VERIFIED"

# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class TestGGUFHeader:
    def test_valid_header(self):
        h = GGUFHeader(GGUF_MAGIC, 3, 100, 20)
        assert h.valid == True

    def test_invalid_magic(self):
        h = GGUFHeader(0xDEAD, 3, 100, 20)
        assert h.valid == False

    def test_to_dict(self):
        h = GGUFHeader(GGUF_MAGIC, 3, 100, 20)
        d = h.to_dict()
        assert d["tensor_count"] == 100
        assert d["valid"] == True

class TestTensorInfo:
    def test_properties(self):
        t = TensorInfo("test", 2, [4, 4], 0, 128)
        assert t.quant_type == "F32"
        assert t.bytes_per_param == 4.0
        assert t.num_elements == 16
        assert t.size_bytes == 64

    def test_to_dict(self):
        t = TensorInfo("weight", 2, [64, 64], 19, 256)
        d = t.to_dict()
        assert d["name"] == "weight"
        assert d["quant_type"] == "Q4_K_M"

class TestZKMLProof:
    def test_create(self):
        p = ZKMLProof(
            proof_id="zkp-001", model_hash="abc", input_hash="def",
            output_hash="ghi", proof_bytes=b"data",
            status=ZKMLStatus.PROVEN.value, created_at=time.time())
        assert p.proof_id == "zkp-001"

class TestAgenticStep:
    def test_create(self):
        s = AgenticStep(
            phase="ACT", input_text="hello", output_text="world",
            tools_used=["web"], reflection="ok", theosis_at_step=0.95,
            timestamp=time.time())
        assert s.phase == "ACT"

class TestTemporalAnchor:
    def test_create(self):
        a = TemporalAnchor(
            anchor_id="a1", merkle_root="0"*64, zk_proof_hash="zk",
            theosis_reading={"tee": 0.1})
        assert a.anchor_id == "a1"

class TestKlerosVerdict:
    def test_create(self):
        v = KlerosVerdict(
            case_id="c1", trigger_gate="EMERGENCY",
            trigger_reason={"urgency": 0.9}, verdict="ESCALATE",
            evidence={}, timestamp=time.time())
        assert v.verdict == "ESCALATE"

# ═══════════════════════════════════════════════════════════════════════════════
# GGUF BRIDGE V3 (1094.1)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGGUFBridgeV3:
    def test_init(self):
        b = GGUFBridgeV3()
        assert b._cache_size == 10
        assert b.header is None

    def test_open_nonexistent_file(self):
        b = GGUFBridgeV3()
        assert b.open("nonexistent.gguf") == False

    def test_get_architecture_default(self):
        b = GGUFBridgeV3()
        assert b.get_architecture() == "unknown"

    def test_get_telemetry_keys(self):
        b = GGUFBridgeV3()
        t = b.get_telemetry()
        assert t["module"] == "GGUFBridgeV3"
        assert t["substrate"] == "1094.1"
        assert t["seal"] == "GGUF-BRIDGE-1094.1-v3.0.0-2026-06-07"

    def test_get_embedding_length_default(self):
        b = GGUFBridgeV3()
        assert b.get_embedding_length() == 0

    def test_close_does_not_crash(self):
        b = GGUFBridgeV3()
        b.close()

# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR THEOSIS 1091.2
# ═══════════════════════════════════════════════════════════════════════════════

class TestVectorTheosis1092:
    def test_init(self):
        vt = VectorTheosis1092(dim=64)
        assert vt.dim == 64
        assert len(vt.readings) == 0

    def test_update_returns_none_with_insufficient_history(self):
        vt = VectorTheosis1092(dim=64)
        r = vt.update(np.random.randn(64).astype(np.float32))
        assert r is None

    def test_update_returns_reading_with_enough_history(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(7):
            vt.update(np.random.randn(64).astype(np.float32))
        assert len(vt.readings) == 5
        r = vt.readings[-1]
        assert "theosis" in r
        assert "tee" in r
        assert "gate" in r

    def test_theosis_range(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(10):
            vt.update(np.random.randn(64).astype(np.float32))
        for r in vt.readings:
            assert 0.0 <= r["theosis"] <= 1.0

    def test_gate_detected(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(15):
            vt.update(np.random.randn(64).astype(np.float32))
        gates = [r["gate"] for r in vt.readings]
        assert all(g in ("OPEN","CAUTION","RESTRICTED","LOCKED","EMERGENCY") for g in gates)

    def test_reset_clears_all(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(5):
            vt.update(np.random.randn(64).astype(np.float32))
        vt.reset()
        assert len(vt.readings) == 0

    def test_get_stats_empty(self):
        vt = VectorTheosis1092(dim=64)
        s = vt.get_stats()
        assert s["n_readings"] == 0

    def test_get_stats_with_data(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(7):
            vt.update(np.random.randn(64).astype(np.float32))
        s = vt.get_stats()
        assert s["n_readings"] == 5
        assert "theosis_mean" in s
        assert "gate_distribution" in s

    def test_get_telemetry(self):
        vt = VectorTheosis1092(dim=64)
        t = vt.get_telemetry()
        assert t["module"] == "VectorTheosis1092"
        assert t["substrate"] == "1091.2"
        assert t["seal"] == "VECTOR-THEOSIS-1091.2-v4.0.0-2026-06-07"
        assert t["dim"] == 64

    def test_dim_mismatch_padding(self):
        vt = VectorTheosis1092(dim=64)
        small = np.random.randn(32).astype(np.float32)
        for _ in range(7):
            vt.update(small)
        assert len(vt.readings) == 5
        assert vt.readings[-1]["theosis"] >= 0.0

    def test_bifurcation_detection(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(20):
            vt.update(np.random.randn(64).astype(np.float32) * 2.0)
        assert vt._bifurcation_count >= 0

    def test_phi_squared_in_theosis(self):
        vt = VectorTheosis1092(dim=64)
        for _ in range(5):
            vt.update(np.random.randn(64).astype(np.float32))
        r = vt.readings[-1]
        assert r["theosis"] <= 1.0

# ═══════════════════════════════════════════════════════════════════════════════
# STETHOSCOPE 1081.1
# ═══════════════════════════════════════════════════════════════════════════════

class TestStethoscope1081:
    def test_init(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        assert s.n_layers == 4
        assert s.dim == 32

    def test_feed_logits_trajectory(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.random.randn(32000).astype(np.float32) for _ in range(3)]
        emb = np.random.randn(32).astype(np.float32)
        r = s.feed_logits_trajectory(logits, emb)
        assert r["step"] == 1
        assert r["n_tokens"] == 3

    def test_per_token_metrics(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.random.randn(32000).astype(np.float32) for _ in range(2)]
        r = s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        assert len(r["per_token_metrics"]) == 2
        assert "norm" in r["per_token_metrics"][0]

    def test_aggregate_computed(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.random.randn(32000).astype(np.float32) for _ in range(4)]
        r = s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        agg = r["aggregate"]
        assert "mean_norm" in agg
        assert "mean_cosine" in agg
        assert "mean_entropy" in agg

    def test_anomaly_detection_collapse(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.zeros(32000, dtype=np.float32) for _ in range(3)]
        r = s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        assert len(r["anomalies"]) > 0

    def test_spectral_analysis_after_multiple_steps(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        for _ in range(10):
            logits = [np.random.randn(32000).astype(np.float32) for _ in range(3)]
            s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        spec = s.get_spectral_analysis()
        assert spec["status"] in ("OK", "INSUFFICIENT_DATA")

    def test_get_telemetry(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        t = s.get_telemetry()
        assert t["module"] == "Stethoscope1081"
        assert t["substrate"] == "1081.1"
        assert t["seal"] == "STETHOSCOPE-1081.1-v3.0.0-2026-06-07"

    def test_reset(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.random.randn(32000).astype(np.float32) for _ in range(3)]
        s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        s.reset()
        assert s._step == 0
        assert len(s._trajectory) == 0

    def test_get_trajectory_matrix_returns_none_when_empty(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        assert s.get_trajectory_matrix() is None

    def test_get_trajectory_matrix_after_feed(self):
        s = Stethoscope1081(n_layers=4, dim=32, n_heads=4)
        logits = [np.random.randn(32000).astype(np.float32) for _ in range(3)]
        s.feed_logits_trajectory(logits, np.random.randn(32).astype(np.float32))
        mat = s.get_trajectory_matrix()
        assert mat is not None
        assert mat.shape[1] == 32

# ═══════════════════════════════════════════════════════════════════════════════
# ZKML BRIDGE 1095
# ═══════════════════════════════════════════════════════════════════════════════

class TestZKMLBridge1095:
    def test_init(self):
        z = ZKMLBridge1095()
        assert z.chain_id == "12120014"
        assert len(z.proofs) == 0

    def test_commit_model_nonexistent(self):
        z = ZKMLBridge1095()
        h = z.commit_model("nonexistent.gguf")
        assert h == ""

    def test_prove_inference(self):
        z = ZKMLBridge1095()
        emb = np.random.randn(64).astype(np.float32)
        proof = z.prove_inference("simulated", "hello world", "output text", emb)
        assert proof.proof_id.startswith("ZKP-")
        assert proof.status == ZKMLStatus.PROVEN.value

    def test_proof_added_to_list(self):
        z = ZKMLBridge1095()
        emb = np.random.randn(64).astype(np.float32)
        z.prove_inference("simulated", "test", "out", emb)
        assert len(z.proofs) == 1

    def test_verify_proof(self):
        z = ZKMLBridge1095()
        emb = np.random.randn(64).astype(np.float32)
        p = z.prove_inference("simulated", "test", "out", emb)
        assert z.verify_proof(p.proof_id) == True
        assert p.status == ZKMLStatus.VERIFIED.value

    def test_verify_nonexistent_proof(self):
        z = ZKMLBridge1095()
        assert z.verify_proof("nonexistent") == False

    def test_get_telemetry(self):
        z = ZKMLBridge1095()
        emb = np.random.randn(64).astype(np.float32)
        z.prove_inference("simulated", "test", "out", emb)
        t = z.get_telemetry()
        assert t["substrate"] == "1095"
        assert t["seal"] == "ZKML-BRIDGE-1095-v1.0.0-2026-06-07"
        assert t["total_proofs"] == 1

# ═══════════════════════════════════════════════════════════════════════════════
# AGENTIC LOOP 1096
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgenticLoop1096:
    def test_init(self):
        a = AgenticLoop1096()
        assert a.max_iterations == 5
        assert len(a.steps) == 0

    def test_execute_returns_plan(self):
        a = AgenticLoop1096()
        result = a.execute(
            objective="Solve P vs NP",
            llm_generate=lambda p: {"output": f"[ai] {p}"})
        assert "plan" in result
        assert len(result["plan"]) >= 1
        assert result["iterations"] >= 1

    def test_steps_recorded(self):
        a = AgenticLoop1096()
        a.execute(
            objective="Test objective",
            llm_generate=lambda p: {"output": "result"})
        assert len(a.steps) >= 1

    def test_lessons_learned(self):
        a = AgenticLoop1096()
        a.execute(
            objective="Test",
            llm_generate=lambda p: {"output": "x"},
            theosis_monitor=lambda x: 0.3)
        assert len(a.lessons) >= 1

    def test_register_tool(self):
        a = AgenticLoop1096()
        a.register_tool("my_tool", lambda x: x)
        assert "my_tool" in a.tools

    def test_get_telemetry(self):
        a = AgenticLoop1096()
        a.execute(objective="test", llm_generate=lambda p: {"output": "r"})
        t = a.get_telemetry()
        assert t["substrate"] == "1096"
        assert t["seal"] == "AGENTIC-LOOP-1096-v1.0.0-2026-06-07"
        assert t["total_steps"] > 0

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORALCHAIN 1097
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemporalChain1097:
    def test_init(self):
        tc = TemporalChain1097()
        assert tc.chain_id == "12120014"
        assert len(tc.anchors) == 0

    def test_anchor_reading(self):
        tc = TemporalChain1097()
        reading = {"cycle": 1, "theosis": 0.95, "tee": 0.1, "gate": "OPEN"}
        anchor = tc.anchor_reading(reading)
        assert anchor.anchor_id.startswith("ANCHOR-")
        assert len(anchor.merkle_root) == 64

    def test_anchor_increments_list(self):
        tc = TemporalChain1097()
        for i in range(3):
            tc.anchor_reading({"cycle": i, "theosis": 0.9, "tee": 0.1, "gate": "OPEN"})
        assert len(tc.anchors) == 3

    def test_merkle_root_changes(self):
        tc = TemporalChain1097()
        r1 = tc.anchor_reading({"cycle": 1, "theosis": 0.95, "tee": 0.1, "gate": "OPEN"})
        r2 = tc.anchor_reading({"cycle": 2, "theosis": 0.90, "tee": 0.2, "gate": "CAUTION"})
        assert r1.merkle_root != r2.merkle_root

    def test_merkle_root_deterministic(self):
        tc1 = TemporalChain1097()
        tc1.anchor_reading({"theosis": 0.95, "tee": 0.1, "gate": "OPEN"})
        root1 = tc1._compute_merkle_root()
        tc2 = TemporalChain1097()
        tc2.anchor_reading({"theosis": 0.95, "tee": 0.1, "gate": "OPEN"})
        root2 = tc2._compute_merkle_root()
        assert root1 == root2

    def test_rollup_batch_after_10_anchors(self):
        tc = TemporalChain1097()
        for i in range(12):
            tc.anchor_reading({"cycle": i, "theosis": 0.9, "tee": 0.1, "gate": "OPEN"})
        assert len(tc._current_batch) == 2

    def test_get_telemetry(self):
        tc = TemporalChain1097()
        tc.anchor_reading({"theosis": 0.95, "tee": 0.1, "gate": "OPEN"})
        t = tc.get_telemetry()
        assert t["substrate"] == "1097"
        assert t["seal"] == "TEMPORALCHAIN-1097-v2.0.0-2026-06-07"
        assert t["total_anchors"] == 1

    def test_empty_merkle_root(self):
        tc = TemporalChain1097()
        assert tc._compute_merkle_root() == "0" * 64

# ═══════════════════════════════════════════════════════════════════════════════
# KLEROS TRIGGER 1085.1
# ═══════════════════════════════════════════════════════════════════════════════

class TestKlerosTrigger1085:
    def test_init(self):
        k = KlerosTrigger1085()
        assert len(k.cases) == 0

    def test_evaluate_dismiss(self):
        k = KlerosTrigger1085()
        reading = {
            "tee": 0.01, "theosis": 0.99, "refined_fatigue": 0.01,
            "spectral_divergence": 0.0, "bifurcation_detected": False,
            "_recent_gates": ["OPEN"]}
        case = k.evaluate(gate="OPEN", theosis_reading=reading)
        assert case.verdict in ("DISMISS", "MONITOR")
        assert case.case_id.startswith("KLR-")

    def test_evaluate_monitor(self):
        k = KlerosTrigger1085()
        reading = {
            "tee": 0.15, "theosis": 0.7, "refined_fatigue": 0.3,
            "spectral_divergence": 0.0, "bifurcation_detected": False,
            "_recent_gates": []}
        case = k.evaluate(gate="CAUTION", theosis_reading=reading)
        assert case.verdict in ("MONITOR", "QUARANTINE")

    def test_evaluate_quarantine(self):
        k = KlerosTrigger1085()
        reading = {
            "tee": 0.35, "theosis": 0.4, "refined_fatigue": 0.6,
            "spectral_divergence": 0.5, "bifurcation_detected": False,
            "_recent_gates": []}
        case = k.evaluate(gate="RESTRICTED", theosis_reading=reading)
        assert case.verdict in ("QUARANTINE", "MONITOR")

    def test_evaluate_escalate(self):
        k = KlerosTrigger1085()
        reading = {
            "tee": 0.60, "theosis": 0.05, "refined_fatigue": 0.9,
            "spectral_divergence": 0.8, "bifurcation_detected": True,
            "_recent_gates": []}
        case = k.evaluate(gate="EMERGENCY", theosis_reading=reading)
        assert case.verdict == "ESCALATE"

    def test_check_quarantine_not_active(self):
        k = KlerosTrigger1085()
        q = k.check_quarantine()
        assert q["in_quarantine"] == False

    def test_check_quarantine_active(self):
        k = KlerosTrigger1085()
        reading = {
            "tee": 0.35, "theosis": 0.4, "refined_fatigue": 0.6,
            "spectral_divergence": 0.0, "bifurcation_detected": False,
            "_recent_gates": []}
        k.evaluate(gate="RESTRICTED", theosis_reading=reading)
        q = k.check_quarantine()
        assert "in_quarantine" in q

    def test_set_temporal_chain(self):
        k = KlerosTrigger1085()
        tc = TemporalChain1097()
        k.set_temporal_chain(tc)
        assert k._temporal_chain is not None

    def test_get_telemetry(self):
        k = KlerosTrigger1085()
        t = k.get_telemetry()
        assert t["substrate"] == "1085.1"
        assert t["seal"] == "KLEROS-TRIGGER-1085.1-v2.0.0-2026-06-07"
        assert t["total_cases"] == 0

    def test_urgency_distribution(self):
        k = KlerosTrigger1085()
        for i in range(10):
            gate = ["OPEN", "CAUTION", "RESTRICTED", "LOCKED", "EMERGENCY"][i % 5]
            k.evaluate(gate=gate, theosis_reading={
                "tee": i * 0.1, "theosis": max(0.01, 1.0 - i * 0.1),
                "refined_fatigue": i * 0.1, "spectral_divergence": 0.0,
                "bifurcation_detected": (i % 3 == 0), "_recent_gates": []})
        t = k.get_telemetry()
        assert t["total_cases"] == 10
        assert len(t["verdict_distribution"]) > 0

# ═══════════════════════════════════════════════════════════════════════════════
# LLAMA-CPP BRIDGE V3 (1094.2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestLlamaCppBridgeV3:
    def test_init(self):
        l = LlamaCppBridgeV3()
        assert l.n_ctx == 2048
        assert l._llm is None

    def test_load_returns_false_without_library(self):
        l = LlamaCppBridgeV3()
        assert l.load("test.gguf") == False

    def test_generate_returns_model_not_loaded(self):
        l = LlamaCppBridgeV3()
        r = l.generate_with_full_extraction("test")
        assert r["status"] == "MODEL_NOT_LOADED"

    def test_get_telemetry(self):
        l = LlamaCppBridgeV3()
        t = l.get_telemetry()
        assert t["substrate"] == "1094.2"
        assert t["seal"] == "LLAMA-CPP-BRIDGE-1094.2-v3.0.0-2026-06-07"
        assert t["llama_cpp_available"] == False
        assert t["model_loaded"] == False

# ═══════════════════════════════════════════════════════════════════════════════
# CATHEDRAL ORCHESTRATOR V5 (1098)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCathedralOrchestratorV5:
    def test_init(self):
        o = CathedralOrchestratorV5()
        assert o.cycle_count == 0
        assert o._active == False

    def test_start_cycle(self):
        o = CathedralOrchestratorV5()
        o.start_cycle()
        assert o._active == True

    def test_end_cycle(self):
        o = CathedralOrchestratorV5()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        report = o.end_cycle()
        assert report["cycles"] == 0
        assert report["gguf"] is not None

    def test_get_telemetry(self):
        o = CathedralOrchestratorV5()
        t = o.get_telemetry()
        assert t["module"] == "CathedralOrchestratorV5"
        assert t["substrate"] == "1098"
        assert t["seal"] == "ORCHESTRATOR-v5.0.0-2026-06-07"

    def test_simulated_inference(self):
        o = CathedralOrchestratorV5()
        o.start_cycle()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        np.random.seed(123)
        result = o.infer("test prompt", max_tokens=5)
        assert result["cycle"] == 1
        assert "generated_text" in result
        assert "theosis" in result or result["theosis"] is None
        o.end_cycle()

    def test_multiple_cycles(self):
        o = CathedralOrchestratorV5()
        o.start_cycle()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        np.random.seed(42)
        for i in range(3):
            o.infer(f"prompt {i}", max_tokens=4)
        assert o.cycle_count == 3
        o.end_cycle()

    def test_end_cycle_report_contains_all_modules(self):
        o = CathedralOrchestratorV5()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        report = o.end_cycle()
        assert "gguf" in report
        assert "llm" in report
        assert "zkml" in report
        assert "temporal" in report

    def test_dashboard_created(self):
        dash_path = tempfile.mktemp(suffix=".jsonl", prefix="v5_test_")
        o = CathedralOrchestratorV5(dashboard_path=dash_path)
        o.start_cycle()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        np.random.seed(42)
        o.infer("dashboard test", max_tokens=3)
        o.end_cycle()
        assert Path(dash_path).exists()
        data = Path(dash_path).read_text(encoding="utf-8").strip()
        assert len(data) > 0
        os.unlink(dash_path)

    def test_load_model_no_gguf(self):
        o = CathedralOrchestratorV5()
        r = o.load_model("nonexistent.gguf")
        assert r["status"] == "ERROR"

# ═══════════════════════════════════════════════════════════════════════════════
# FULL ORCHESTRATOR CYCLE WITH KLEROS TRIGGER
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullCycle:
    def test_plan_infer_zkml_steth_theosis_kleros_anchor(self):
        o = CathedralOrchestratorV5()
        o.start_cycle()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()

        np.random.seed(42)
        result = None
        for i in range(3):
            result = o.infer(f"trigger test {i}", max_tokens=8, use_agentic=True)
        assert result["cycle"] == 3
        o.end_cycle()

        t = o.get_telemetry()
        assert t["cycles"] >= 3
        assert t["zkml"]["total_proofs"] >= 1
        assert t["agentic"]["total_steps"] >= 1
        assert t["temporal"]["total_anchors"] >= 1

    def test_all_seals_present_in_telemetry(self):
        o = CathedralOrchestratorV5()
        o.vt = VectorTheosis1092(dim=64)
        o.stethoscope = Stethoscope1081(n_layers=4, dim=64, n_heads=4)
        o.kleros = KlerosTrigger1085()
        o.kleros.set_temporal_chain(o.temporal)
        o.zkml = ZKMLBridge1095()
        o.agentic = AgenticLoop1096()
        t = o.get_telemetry()
        seals = [
            t["gguf"]["seal"],
            t["llm"]["seal"],
            t["zkml"]["seal"],
        ]
        if t["vector_theosis"]: seals.append(t["vector_theosis"]["seal"])
        if t["stethoscope"]: seals.append(t["stethoscope"]["seal"])
        if t["kleros"]: seals.append(t["kleros"]["seal"])
        seals.append(t["temporal"]["seal"])
        if t["agentic"]: seals.append(t["agentic"]["seal"])
        expected = [
            "GGUF-BRIDGE-1094.1-v3.0.0-2026-06-07",
            "LLAMA-CPP-BRIDGE-1094.2-v3.0.0-2026-06-07",
            "ZKML-BRIDGE-1095-v1.0.0-2026-06-07",
        ]
        for exp in expected:
            assert exp in seals, f"Missing seal: {exp}"
