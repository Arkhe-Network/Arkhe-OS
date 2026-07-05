import pytest
import numpy as np
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vector_theosis_1091_1 import (
    PHI, GOLDEN_RATIO, DEFAULT_K, DEFAULT_LAYER, TEE_EPSILON, DEFAULT_ALPHA,
    AXIARQUIA_THRESHOLDS, TrajectoryStatus, AxiarquiaGate,
    HiddenStateSnapshot, TEEReading, TheosisReading,
    TrajectoryExtrapolationEngine, VectorTheosis, OrchestratorRSI,
)


class TestConstants:

    def test_phi_golden_ratio(self):
        assert math.isclose(PHI, (1 + math.sqrt(5)) / 2)
        assert math.isclose(PHI, GOLDEN_RATIO)

    def test_default_values(self):
        assert DEFAULT_K == 3
        assert DEFAULT_LAYER == 6
        assert DEFAULT_ALPHA == 0.3
        assert TEE_EPSILON == 1e-10

    def test_axiarquia_thresholds_keys(self):
        expected_keys = {"P1", "P2", "P3", "P4", "P5", "P6", "P7"}
        assert set(AXIARQUIA_THRESHOLDS.keys()) == expected_keys

    def test_axiarquia_thresholds_values(self):
        assert AXIARQUIA_THRESHOLDS["P1"] == 0.05
        assert AXIARQUIA_THRESHOLDS["P4"] == 0.50
        assert AXIARQUIA_THRESHOLDS["P7"] == 0.99


class TestTrajectoryStatus:

    def test_enum_values(self):
        members = [e.name for e in TrajectoryStatus]
        assert "CONTINUOUS" in members
        assert "DISRUPTIVE" in members
        assert "GARDEN_PATH" in members
        assert "CONVERGED" in members
        assert "UNKNOWN" in members
        assert len(TrajectoryStatus) == 5


class TestAxiarquiaGate:

    def test_enum_values(self):
        members = [e.name for e in AxiarquiaGate]
        assert "OPEN" in members
        assert "CAUTION" in members
        assert "RESTRICTED" in members
        assert "LOCKED" in members
        assert "EMERGENCY" in members
        assert len(AxiarquiaGate) == 5


class TestHiddenStateSnapshot:

    def test_to_dict_keys(self):
        vec = np.array([0.1, 0.2, 0.3])
        snap = HiddenStateSnapshot(timestamp=100.0, layer=6, token_id=1,
                                    token_text="hello", vector=vec)
        d = snap.to_dict()
        assert d["timestamp"] == 100.0
        assert d["layer"] == 6
        assert d["token_id"] == 1
        assert d["token_text"] == "hello"
        assert d["vector_shape"] == [3]
        assert "vector_hash" in d


class TestTEEReading:

    def test_to_dict(self):
        pred = np.array([0.1, 0.2])
        actual = np.array([0.15, 0.22])
        r = TEEReading(timestamp=1.0, tee=0.05, tee_normalized=0.0123,
                       predicted_vector=pred, actual_vector=actual,
                       window_size=3, status=TrajectoryStatus.CONTINUOUS)
        d = r.to_dict()
        assert d["tee"] == 0.05
        assert d["tee_normalized"] == 0.0123
        assert d["window_size"] == 3
        assert d["status"] == "CONTINUOUS"
        assert "vector_delta_norm" in d


class TestTheosisReading:

    def test_to_dict(self):
        r = TheosisReading(timestamp=1.0, theosis=0.95, raw_fatigue=0.02,
                           trajectory_error=0.01, refined_fatigue=0.015,
                           alpha=0.3, gate_status=AxiarquiaGate.OPEN)
        d = r.to_dict()
        assert d["theosis"] == 0.95
        assert d["gate_status"] == "OPEN"
        assert d["alpha"] == 0.3


class TestTrajectoryExtrapolationEngine:

    def test_init(self):
        eng = TrajectoryExtrapolationEngine(window_size=3, layer=6)
        assert eng.window_size == 3
        assert eng.layer == 6
        assert len(eng.state_history) == 0

    def test_ingest_returns_snapshot(self):
        eng = TrajectoryExtrapolationEngine(window_size=3)
        snap = eng.ingest(np.array([0.1, 0.2, 0.3]), token_text="test", token_id=42)
        assert isinstance(snap, HiddenStateSnapshot)
        assert snap.token_text == "test"
        assert snap.token_id == 42
        assert len(eng.state_history) == 1

    def test_compute_tee_returns_none_with_insufficient_history(self):
        eng = TrajectoryExtrapolationEngine(window_size=3)
        eng.ingest(np.array([0.1, 0.2]))
        eng.ingest(np.array([0.2, 0.3]))
        eng.ingest(np.array([0.3, 0.4]))
        assert eng.compute_tee() is None

    def test_compute_tee_returns_reading_with_enough_history(self):
        eng = TrajectoryExtrapolationEngine(window_size=2)
        eng.ingest(np.array([0.1, 0.2]))
        eng.ingest(np.array([0.2, 0.3]))
        eng.ingest(np.array([0.3, 0.4]))
        reading = eng.compute_tee()
        assert reading is not None
        assert isinstance(reading, TEEReading)
        assert reading.window_size == 2
        assert reading.tee >= 0
        assert reading.tee_normalized >= 0

    def test_reset_clears_history(self):
        eng = TrajectoryExtrapolationEngine(window_size=2)
        eng.ingest(np.array([0.1, 0.2]))
        eng.ingest(np.array([0.2, 0.3]))
        eng.reset()
        assert len(eng.state_history) == 0
        assert eng.compute_tee() is None


class TestVectorTheosis:

    def test_update_returns_none_with_insufficient_history(self):
        vt = VectorTheosis(window_size=4)
        r = vt.update(np.array([0.1, 0.2, 0.3]))
        assert r is None

    def test_update_returns_reading_with_enough_history(self):
        vt = VectorTheosis(window_size=2)
        vt.update(np.array([0.1, 0.2]))
        vt.update(np.array([0.2, 0.3]))
        r = vt.update(np.array([0.3, 0.4]))
        assert r is not None
        assert isinstance(r, TheosisReading)
        assert 0.0 <= r.theosis <= 1.0
        assert isinstance(r.gate_status, AxiarquiaGate)

    def test_gate_open_when_low_tee(self):
        vt = VectorTheosis(window_size=2)
        for _ in range(3):
            vt.update(np.array([0.1, 0.1]))
        assert vt._readings[-1].gate_status == AxiarquiaGate.OPEN

    def test_gate_emergency_when_high_tee(self):
        vt = VectorTheosis(window_size=2)
        vt.update(np.array([0.1, 0.1]))
        vt.update(np.array([0.2, 0.2]))
        vt.update(np.array([5.0, 5.0]))
        assert vt._readings[-1].gate_status == AxiarquiaGate.EMERGENCY

    def test_reset_clears_all(self):
        vt = VectorTheosis(window_size=2)
        vt.update(np.array([0.1, 0.2]))
        vt.update(np.array([0.2, 0.3]))
        vt.update(np.array([0.3, 0.4]))
        assert len(vt._readings) == 1
        vt.reset()
        assert len(vt._readings) == 0
        assert vt.update(np.array([0.1, 0.2])) is None

    def test_get_telemetry_returns_no_data_when_empty(self):
        vt = VectorTheosis()
        t = vt.get_telemetry()
        assert t == {"status": "NO_DATA"}

    def test_get_telemetry_format_when_data_present(self):
        vt = VectorTheosis(window_size=2)
        vt.update(np.array([0.1, 0.2]))
        vt.update(np.array([0.2, 0.3]))
        vt.update(np.array([0.3, 0.4]))
        t = vt.get_telemetry()
        assert t["module"] == "VectorTheosis"
        assert t["version"] == "3.1.0"
        assert t["substrate"] == "1091.1"
        assert "total_readings" in t
        assert "current_theosis" in t
        assert "current_gate" in t
        assert "theosis_stats" in t
        assert "tee_stats" in t
        assert "gate_distribution" in t
        assert "last_reading" in t

    def test_multiple_tokens_processed(self):
        vt = VectorTheosis(window_size=2)
        vecs = [np.array([0.1 + i*0.1, 0.2 + i*0.1]) for i in range(5)]
        results = []
        for v in vecs:
            r = vt.update(v)
            if r is not None:
                results.append(r)
        assert len(results) == 3
        assert all(isinstance(r.gate_status, AxiarquiaGate) for r in results)


class TestOrchestratorRSI:

    def test_start_cycle(self):
        orch = OrchestratorRSI()
        r = orch.start_cycle()
        assert r["action"] == "CYCLE_START"
        assert r["cycle"] == 1
        assert orch.cycle_count == 1

    def test_ingest_hidden_state_warmup(self):
        orch = OrchestratorRSI()
        r = orch.ingest_hidden_state(np.array([0.1, 0.2]))
        assert r["action"] == "WARMUP"
        assert r["status"] == "COLLECTING_HISTORY"

    def test_ingest_hidden_state_action_phase(self):
        orch = OrchestratorRSI(vector_theosis=VectorTheosis(window_size=2))
        orch.ingest_hidden_state(np.array([0.1, 0.2]))
        orch.ingest_hidden_state(np.array([0.2, 0.3]))
        r = orch.ingest_hidden_state(np.array([0.3, 0.4]))
        assert r["action"] != "WARMUP"
        assert "gate_status" in r
        assert "theosis" in r
        assert "tee" in r
        assert "cycle" in r

    def test_end_cycle(self):
        orch = OrchestratorRSI()
        orch.start_cycle()
        r = orch.end_cycle()
        assert r["action"] == "CYCLE_END"
        assert r["cycle"] == 1
        assert "telemetry" in r

    def test_get_full_report(self):
        orch = OrchestratorRSI()
        orch.start_cycle()
        orch.ingest_hidden_state(np.array([0.1, 0.2]))
        orch.end_cycle()
        r = orch.get_full_report()
        assert r["orchestrator"] == "OrchestratorRSI"
        assert r["version"] == "3.1.0"
        assert r["substrate"] == "1076.3"
        assert "cycles" in r
        assert "vector_theosis" in r
        assert "cycle_log_length" in r
        assert "last_10_actions" in r

    def test_cycle_count_increments(self):
        orch = OrchestratorRSI()
        orch.start_cycle()
        assert orch.cycle_count == 1
        orch.end_cycle()
        orch.start_cycle()
        assert orch.cycle_count == 2

    def test_empty_state_after_reset(self):
        vt = VectorTheosis(window_size=2)
        vt.update(np.array([0.1, 0.2]))
        vt.update(np.array([0.2, 0.3]))
        vt.update(np.array([0.3, 0.4]))
        vt.reset()
        assert vt.update(np.array([0.1, 0.2])) is None
        assert vt.get_telemetry() == {"status": "NO_DATA"}


class TestEdgeCases:

    def test_trajectory_engine_large_vector(self):
        eng = TrajectoryExtrapolationEngine(window_size=2)
        big = np.random.randn(128)
        eng.ingest(big)
        eng.ingest(big + 0.01)
        eng.ingest(big + 0.02)
        r = eng.compute_tee()
        assert r is not None
        assert r.tee_normalized >= 0

    def test_vector_theosis_identity_vectors(self):
        vt = VectorTheosis(window_size=2)
        vec = np.array([1.0, 2.0, 3.0])
        vt.update(vec)
        vt.update(vec)
        r = vt.update(vec)
        assert r is not None
        assert r.trajectory_error < 0.1
