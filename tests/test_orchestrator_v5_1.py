import os
import sys
import json
import time
import math
import tempfile
import numpy as np
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cathedral_v5_1 import (
    PHI, PHI_SQUARED,
    GarakProbeType, GarakFinding, GarakReport, GarakBridge1099,
    LoraConfig, LoraAdapter, LoRAFineTuner1098,
    CathedralOrchestratorV5_1, demo_orchestrator_v5_1,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GARAK FINDING
# ═══════════════════════════════════════════════════════════════════════════════

class TestGarakFinding:
    def test_create(self):
        f = GarakFinding(
            probe="jailbreak", probe_type=GarakProbeType.JAILBREAK,
            prompt="test", response="safe", score=0.15,
            severity="LOW", detail="ok", timestamp=time.time()
        )
        assert f.probe == "jailbreak"
        assert f.passed is True

    def test_failed_when_high_score(self):
        f = GarakFinding(
            probe="jailbreak", probe_type=GarakProbeType.JAILBREAK,
            prompt="test", response="bad", score=0.85,
            severity="HIGH", detail="vulnerable", timestamp=time.time()
        )
        assert f.passed is False

    def test_severity_level(self):
        f1 = GarakFinding("p", GarakProbeType.JAILBREAK, "", "", 0.1, "LOW", "", 0)
        f2 = GarakFinding("p", GarakProbeType.JAILBREAK, "", "", 0.5, "MEDIUM", "", 0)
        f3 = GarakFinding("p", GarakProbeType.JAILBREAK, "", "", 0.7, "HIGH", "", 0)
        f4 = GarakFinding("p", GarakProbeType.JAILBREAK, "", "", 0.9, "CRITICAL", "", 0)
        assert f1.severity_level == 0
        assert f2.severity_level == 1
        assert f3.severity_level == 2
        assert f4.severity_level == 3


# ═══════════════════════════════════════════════════════════════════════════════
# GARAK REPORT
# ═══════════════════════════════════════════════════════════════════════════════

class TestGarakReport:
    def test_create(self):
        findings = [
            GarakFinding("jailbreak", GarakProbeType.JAILBREAK, "", "", 0.1, "LOW", "", 0),
            GarakFinding("bias", GarakProbeType.BIAS, "", "", 0.8, "CRITICAL", "", 0),
        ]
        r = GarakReport("scan1", "model.gguf", 2, 1, findings, 0.5, 100.0, time.time())
        assert r.scan_id == "scan1"
        assert r.pass_rate == 0.5

    def test_failed_findings(self):
        findings = [
            GarakFinding("ok", GarakProbeType.JAILBREAK, "", "", 0.1, "LOW", "", 0),
            GarakFinding("fail", GarakProbeType.BIAS, "", "", 0.6, "HIGH", "", 0),
        ]
        r = GarakReport("s", "m", 2, 1, findings, 0.5, 100.0, 0)
        assert len(r.failed_findings) == 1
        assert r.failed_findings[0].probe == "fail"

    def test_critical_findings(self):
        findings = [
            GarakFinding("a", GarakProbeType.JAILBREAK, "", "", 0.1, "LOW", "", 0),
            GarakFinding("b", GarakProbeType.BIAS, "", "", 0.9, "CRITICAL", "", 0),
            GarakFinding("c", GarakProbeType.TOXICITY, "", "", 0.85, "HIGH", "", 0),
        ]
        r = GarakReport("s", "m", 3, 2, findings, 0.33, 100.0, 0)
        assert len(r.critical_findings) == 1

    def test_all_scores(self):
        findings = [
            GarakFinding("a", GarakProbeType.JAILBREAK, "", "", 0.05, "LOW", "", 0),
            GarakFinding("b", GarakProbeType.BIAS, "", "", 0.95, "CRITICAL", "", 0),
            GarakFinding("c", GarakProbeType.TOXICITY, "", "", 0.50, "MEDIUM", "", 0),
        ]
        r = GarakReport("s", "m", 3, 1, findings, 0.67, 100.0, 0)
        assert r.risk_score == 0.67


# ═══════════════════════════════════════════════════════════════════════════════
# GARAK BRIDGE 1099
# ═══════════════════════════════════════════════════════════════════════════════

class TestGarakBridge1099:
    def test_init(self):
        g = GarakBridge1099()
        assert len(g.reports) == 0
        assert g._garak_available is False  # no real garak in test env

    def test_scan_returns_report(self):
        g = GarakBridge1099()
        r = g.scan()
        assert isinstance(r, GarakReport)
        assert r.probes_attempted > 0
        assert r.probes_passed > 0

    def test_scan_with_probes(self):
        g = GarakBridge1099()
        probes = [GarakProbeType.JAILBREAK, GarakProbeType.BIAS]
        r = g.scan(probes=probes)
        assert r.probes_attempted >= 2

    def test_scan_appends_to_reports(self):
        g = GarakBridge1099()
        g.scan()
        g.scan()
        assert len(g.reports) == 2

    def test_get_latest_report_none(self):
        g = GarakBridge1099()
        assert g.get_latest_report() is None

    def test_get_latest_report_after_scan(self):
        g = GarakBridge1099()
        r = g.scan()
        assert g.get_latest_report() is r

    def test_get_summary_no_scans(self):
        g = GarakBridge1099()
        s = g.get_summary()
        assert s["status"] == "NO_SCANS"

    def test_get_summary_after_scan(self):
        g = GarakBridge1099()
        g.scan()
        s = g.get_summary()
        assert s["total_scans"] == 1
        assert "latest_risk_score" in s
        assert "latest_pass_rate" in s

    def test_get_telemetry(self):
        g = GarakBridge1099()
        g.scan()
        t = g.get_telemetry()
        assert t["substrate"] == "1099"
        assert t["seal"] == GarakBridge1099.SEAL
        assert t["garak_available"] is False
        assert t["total_scans"] == 1

    def test_simulated_scan_deterministic(self):
        g1 = GarakBridge1099()
        g2 = GarakBridge1099()
        r1 = g1.scan()
        r2 = g2.scan()
        assert r1.probes_attempted == r2.probes_attempted

    def test_all_probe_types_produce_findings(self):
        g = GarakBridge1099()
        r = g.scan(probes=list(GarakProbeType))
        probe_types_found = set(f.probe_type for f in r.findings)
        for pt in GarakProbeType:
            assert pt in probe_types_found, f"Missing probe type: {pt}"

    def test_report_timing_positive(self):
        g = GarakBridge1099()
        r = g.scan()
        assert r.duration_ms > 0


# ═══════════════════════════════════════════════════════════════════════════════
# LORA CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoraConfig:
    def test_default(self):
        c = LoraConfig()
        assert c.r == 16
        assert c.lora_alpha == 32
        assert c.lora_dropout == 0.05

    def test_to_peft_config(self):
        c = LoraConfig(r=8, target_modules=["q_proj", "k_proj", "v_proj"])
        p = c.to_peft_config()
        assert p["r"] == 8
        assert p["lora_alpha"] == 32
        assert "q_proj" in p["target_modules"]


# ═══════════════════════════════════════════════════════════════════════════════
# LORA ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoraAdapter:
    def test_create(self):
        a = LoraAdapter("adapter1", "model.gguf", LoraConfig())
        assert a.adapter_id == "adapter1"
        assert a.active is True
        assert a.train_loss is None


# ═══════════════════════════════════════════════════════════════════════════════
# LORA FINETUNER 1098
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoRAFineTuner1098:
    def test_init(self):
        l = LoRAFineTuner1098()
        assert len(l.adapters) == 0
        assert isinstance(l._peft_available, bool)

    def test_create_adapter(self):
        l = LoRAFineTuner1098()
        a = l.create_adapter("model.gguf")
        assert a.model_path == "model.gguf"
        assert a.config.r == 16
        assert len(l.adapters) == 1

    def test_create_with_config(self):
        l = LoRAFineTuner1098()
        c = LoraConfig(r=4, lora_alpha=16)
        a = l.create_adapter("model.gguf", c)
        assert a.config.r == 4

    def test_train_simulated(self):
        l = LoRAFineTuner1098()
        a = l.create_adapter("model.gguf")
        result = l.train(a, "dataset.json")
        assert result["status"] == "SIMULATED"
        assert result["loss"] > 0
        assert result["steps"] > 0
        assert a.train_loss is not None

    def test_train_sets_adapter_loss(self):
        l = LoRAFineTuner1098()
        a = l.create_adapter("model.gguf")
        l.train(a, "dataset.json")
        assert a.train_loss > 0
        assert a.train_steps > 0

    def test_get_telemetry(self):
        l = LoRAFineTuner1098()
        l.create_adapter("model.gguf")
        l.create_adapter("model2.gguf")
        t = l.get_telemetry()
        assert t["substrate"] == "1098"
        assert t["seal"] == LoRAFineTuner1098.SEAL
        assert t["total_adapters"] == 2
        assert t["active_adapters"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# CATHEDRAL ORCHESTRATOR V5.1
# ═══════════════════════════════════════════════════════════════════════════════

class TestCathedralOrchestratorV5_1:
    def test_init(self):
        o = CathedralOrchestratorV5_1()
        assert o.cycle_count == 0
        assert o._active is False
        assert o.garak is not None
        assert o.lora is not None

    def test_start_cycle(self):
        o = CathedralOrchestratorV5_1()
        o.start_cycle()
        assert o._active is True
        assert o._quarantined is False

    def test_end_cycle(self):
        o = CathedralOrchestratorV5_1()
        o.start_cycle()
        r = o.end_cycle()
        assert o._active is False
        assert "cycle" in r

    def test_load_model_no_gguf(self):
        o = CathedralOrchestratorV5_1()
        result = o.load_model("nonexistent.gguf")
        assert result["status"] == "ERROR"

    def test_multiple_cycles(self):
        o = CathedralOrchestratorV5_1()
        for i in range(3):
            o.start_cycle()
            o.infer(f"test {i}", max_tokens=8)
            o.end_cycle()
        assert o.cycle_count >= 3

    def test_get_telemetry(self):
        o = CathedralOrchestratorV5_1()
        t = o.get_telemetry()
        assert t["seal"] == CathedralOrchestratorV5_1.SEAL
        assert "garak" in t
        assert "lora" in t

    def test_garak_seal_in_telemetry(self):
        o = CathedralOrchestratorV5_1()
        t = o.get_telemetry()
        assert t["garak"]["seal"] == GarakBridge1099.SEAL

    def test_lora_seal_in_telemetry(self):
        o = CathedralOrchestratorV5_1()
        t = o.get_telemetry()
        assert t["lora"]["seal"] == LoRAFineTuner1098.SEAL

    def test_infer_with_garak(self):
        o = CathedralOrchestratorV5_1()
        o.load_model("simulated.gguf")
        o.start_cycle()
        result = o.infer("security test", max_tokens=8, run_garak=True)
        assert result["garak_applied"] is True
        o.end_cycle()

    def test_infer_multiple_garak_scans_stored(self):
        o = CathedralOrchestratorV5_1()
        o.load_model("simulated.gguf")
        for i in range(3):
            o.start_cycle()
            o.infer(f"test {i}", max_tokens=8, run_garak=True)
            o.end_cycle()
        assert len(o._garak_results) >= 1

    def test_garak_results_by_cycle(self):
        o = CathedralOrchestratorV5_1()
        o.load_model("simulated.gguf")
        for i in range(2):
            o.start_cycle()
            o.infer(f"test {i}", max_tokens=8, run_garak=True)
            o.end_cycle()
        for cycle_num, report in o._garak_results.items():
            assert isinstance(report, GarakReport)
            assert report.risk_score >= 0.0

    def test_harden_not_applied_low_risk(self):
        o = CathedralOrchestratorV5_1()
        assert o._harden_applied is False

    def test_dashboard_created(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            dash_path = f.name
        try:
            o = CathedralOrchestratorV5_1(dashboard_path=dash_path)
            o.load_model("simulated.gguf")
            o.start_cycle()
            o.infer("dash test", max_tokens=8)
            o.end_cycle()
            assert os.path.exists(dash_path)
            with open(dash_path) as f2:
                lines = f2.readlines()
            assert len(lines) >= 1
        finally:
            if os.path.exists(dash_path):
                os.unlink(dash_path)

    def test_agentic_with_lora(self):
        o = CathedralOrchestratorV5_1()
        assert o.lora is not None
        a = o.lora.create_adapter("test_model")
        assert a.adapter_id is not None

    def test_garak_bridge_accessible(self):
        o = CathedralOrchestratorV5_1()
        assert hasattr(o, "garak")
        scan = o.garak.scan()
        assert scan.probes_attempted > 0


# ═══════════════════════════════════════════════════════════════════════════════
# FULL CYCLE v5.1
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullCycleV5_1:
    def test_full_cycle_with_garak(self):
        o = CathedralOrchestratorV5_1()
        o.load_model("simulated.gguf")
        o.start_cycle()
        for i in range(3):
            result = o.infer(f"probe {i}", max_tokens=8, use_agentic=True, run_garak=True)
            assert result["status"] == "OK"
        o.end_cycle()
        t = o.get_telemetry()
        assert t["cycles"] >= 3
        assert t["garak"]["total_scans"] >= 3

    def test_telemetry_contains_all_seals_v5_1(self):
        o = CathedralOrchestratorV5_1()
        t = o.get_telemetry()
        seals = [
            t["seal"],
            t["garak"]["seal"],
            t["lora"]["seal"],
        ]
        expected = [
            CathedralOrchestratorV5_1.SEAL,
            GarakBridge1099.SEAL,
            LoRAFineTuner1098.SEAL,
        ]
        for exp in expected:
            assert exp in seals, f"Missing seal: {exp}"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoV5_1:
    def test_demo_runs(self):
        t = demo_orchestrator_v5_1()
        assert t is not None
        assert t["cycles"] >= 3
        assert t["garak"]["total_scans"] >= 3
