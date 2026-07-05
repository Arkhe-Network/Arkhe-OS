import pytest
pytest.importorskip("torch")  # dep pesada opcional
import numpy as np
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cathedral_integration_full import (
    PHI, DEFAULT_K, DEFAULT_ALPHA, DEFAULT_LAYER, TEE_EPSILON,
    AXIARQUIA_THRESHOLDS, TrajectoryStatus, AxiarquiaGate,
    Stethoscope1081, SINDyBridge1089, HamiltonianBridge1053,
    DashboardExporter1064, TrajectoryExtrapolationEngine, VectorTheosis,
    IntegratedOrchestrator1076, DummyLanguageModel, DummyTransformerLayer,
    TEEReading, TheosisReading,
)
import torch


class TestConstants:

    def test_phi_value(self):
        assert np.isclose(PHI, (1 + np.sqrt(5)) / 2)

    def test_defaults(self):
        assert DEFAULT_K == 3
        assert DEFAULT_LAYER == 6
        assert DEFAULT_ALPHA == 0.3

    def test_axiarquia_thresholds(self):
        assert AXIARQUIA_THRESHOLDS["P1"] == 0.05
        assert AXIARQUIA_THRESHOLDS["P7"] == 0.99


class TestEnums:

    def test_trajectory_status_values(self):
        assert len(TrajectoryStatus) == 5
        assert TrajectoryStatus.CONTINUOUS.name == "CONTINUOUS"

    def test_axiarquia_gate_values(self):
        assert len(AxiarquiaGate) == 5
        assert AxiarquiaGate.OPEN.name == "OPEN"
        assert AxiarquiaGate.EMERGENCY.name == "EMERGENCY"


class TestDummyLanguageModel:

    def test_forward_output_shape(self):
        model = DummyLanguageModel(vocab_size=100, hidden_dim=64, num_layers=2)
        model.eval()
        input_ids = torch.tensor([[1, 2, 3]])
        with torch.no_grad():
            out = model(input_ids)
        assert out.shape == (1, 3, 100)

    def test_different_vocab_size(self):
        model = DummyLanguageModel(vocab_size=256, hidden_dim=32, num_layers=2)
        model.eval()
        input_ids = torch.tensor([[0]])
        with torch.no_grad():
            out = model(input_ids)
        assert out.shape == (1, 1, 256)


class TestDummyTransformerLayer:

    def test_forward(self):
        layer = DummyTransformerLayer(hidden_dim=32, num_heads=4)
        x = torch.randn(1, 5, 32)
        out = layer(x)
        assert out.shape == (1, 5, 32)


class TestStethoscope1081:

    def test_init(self):
        s = Stethoscope1081(target_layer=6)
        assert s.target_layer == 6
        assert s._active is False
        assert len(s._captured) == 0

    def test_attach_to_dummy_language_model(self):
        model = DummyLanguageModel(hidden_dim=16, num_layers=2)
        s = Stethoscope1081(target_layer=1)
        s.attach(model)
        assert s._hook_handle is not None
        assert len(s._layer_names) > 0
        s.detach()

    def test_start_stop(self):
        model = DummyLanguageModel(hidden_dim=16, num_layers=2)
        s = Stethoscope1081(target_layer=1)
        s.attach(model)
        s.start()
        assert s._active is True
        model(torch.tensor([[1]]))
        s.stop()
        assert s._active is False
        s.detach()

    def test_get_latest(self):
        model = DummyLanguageModel(hidden_dim=16, num_layers=2)
        s = Stethoscope1081(target_layer=1)
        s.attach(model)
        s.start()
        model(torch.tensor([[1]]))
        model(torch.tensor([[2]]))
        s.stop()
        latest = s.get_latest(n=1)
        assert len(latest) == 1
        assert isinstance(latest[0], np.ndarray)
        s.detach()

    def test_get_telemetry(self):
        model = DummyLanguageModel(hidden_dim=16, num_layers=2)
        s = Stethoscope1081(target_layer=1)
        s.attach(model)
        s.start()
        model(torch.tensor([[1]]))
        s.stop()
        t = s.get_telemetry()
        assert t["module"] == "Stethoscope1081"
        assert t["substrate"] == "1081"
        assert "seal" in t
        assert t["active"] is False
        assert t["total_captured"] > 0
        s.detach()


class TestSINDyBridge1089:

    def test_init(self):
        s = SINDyBridge1089(poly_order=2, threshold=0.1)
        assert s.poly_order == 2
        assert s.threshold == 0.1
        assert s._converged is False

    def test_fit_on_simple_data(self):
        s = SINDyBridge1089(poly_order=2, threshold=0.1)
        X = np.random.randn(50, 2)
        dX = np.random.randn(50, 2)
        s.fit(X, dX)
        assert s._converged is True
        assert s._Xi is not None

    def test_predict_returns_correct_shape(self):
        s = SINDyBridge1089(poly_order=2, threshold=0.1)
        X = np.random.randn(50, 2)
        dX = np.random.randn(50, 2)
        s.fit(X, dX)
        pred = s.predict(X)
        assert pred.shape == (50, 2)

    def test_predict_raises_before_fit(self):
        s = SINDyBridge1089()
        with pytest.raises(RuntimeError):
            s.predict(np.random.randn(10, 2))

    def test_get_equations_returns_list(self):
        s = SINDyBridge1089(poly_order=2, threshold=0.1)
        X = np.random.randn(50, 2)
        dX = np.random.randn(50, 2)
        s.fit(X, dX)
        eqs = s.get_equations()
        assert isinstance(eqs, list)
        assert len(eqs) == 2
        assert all("dx" in e for e in eqs)

    def test_get_sparsity(self):
        s = SINDyBridge1089(poly_order=2, threshold=0.5)
        X = np.random.randn(50, 2)
        dX = np.random.randn(50, 2)
        s.fit(X, dX)
        sp = s.get_sparsity()
        assert 0.0 <= sp <= 1.0

    def test_get_sparsity_before_fit(self):
        s = SINDyBridge1089()
        assert s.get_sparsity() == 0.0

    def test_get_telemetry(self):
        s = SINDyBridge1089()
        t = s.get_telemetry()
        assert t["module"] == "SINDyBridge1089"
        assert t["substrate"] == "1089"
        assert "seal" in t


class TestHamiltonianBridge1053:

    def test_init(self):
        h = HamiltonianBridge1053(taylor_order=10, max_backtrack=3)
        assert h.taylor_order == 10
        assert h.max_backtrack == 3

    def test_reverse_returns_array(self):
        h = HamiltonianBridge1053()
        current = np.array([0.1, 0.2, 0.3])
        result = h.reverse(current)
        assert isinstance(result, np.ndarray)
        assert result.shape == (3,)

    def test_reverse_with_insufficient_history_falls_back(self):
        h = HamiltonianBridge1053()
        r1 = h.reverse(np.array([0.1, 0.2]))
        r2 = h.reverse(np.array([0.2, 0.3]))
        assert len(h._history) == 2

    def test_reverse_converges_with_sufficient_history(self):
        h = HamiltonianBridge1053(taylor_order=5, max_backtrack=5)
        states = [np.array([i * 0.1, i * 0.1 + 0.5]) for i in range(5)]
        results = [h.reverse(s) for s in states]
        assert len(results) == 5
        assert results[-1].shape == (2,)

    def test_get_telemetry(self):
        h = HamiltonianBridge1053()
        t = h.get_telemetry()
        assert t["module"] == "HamiltonianBridge1053"
        assert t["substrate"] == "1053.4"
        assert "seal" in t
        assert "history_size" in t


class TestDashboardExporter1064:

    def test_init_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            assert os.path.exists(tmpdir)
            assert d._total_records == 0
            assert d.buffer_size == 10

    def test_emit_increments_total(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            d.emit({"event": "test"})
            assert d._total_records == 1
            d.emit({"event": "test2"})
            assert d._total_records == 2

    def test_close_flushes_buffer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            d.emit({"event": "test"})
            d.close()
            files = os.listdir(tmpdir)
            assert len(files) > 0

    def test_get_telemetry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            t = d.get_telemetry()
            assert t["module"] == "DashboardExporter1064"
            assert t["substrate"] == "1064.2"
            assert "seal" in t
            assert t["total_records"] == 0
            assert t["buffered"] == 0


class TestTrajectoryExtrapolationEngine:

    def test_ingest_and_compute_tee(self):
        eng = TrajectoryExtrapolationEngine(window_size=2)
        for i in range(3):
            eng.ingest(np.array([float(i), float(i+1)]))
        r = eng.compute_tee()
        assert r is not None
        assert r.tee >= 0

    def test_tee_returns_none_with_insufficient(self):
        eng = TrajectoryExtrapolationEngine(window_size=3)
        eng.ingest(np.array([0.1, 0.2]))
        assert eng.compute_tee() is None


class TestVectorTheosis:

    def test_update_with_fake_hidden_states(self):
        vt = VectorTheosis(window_size=2)
        for i in range(3):
            vt.update(np.array([float(i) * 0.1, float(i) * 0.1 + 0.5]))
        assert len(vt._readings) == 1
        assert 0.0 <= vt._readings[-1].theosis <= 1.0


class TestIntegratedOrchestrator1076:

    def test_init(self):
        orch = IntegratedOrchestrator1076()
        assert orch.cycle_count == 0
        assert orch.emergency_count == 0
        assert orch.garden_path_count == 0

    def test_attach_model(self):
        model = DummyLanguageModel(hidden_dim=16, num_layers=2)
        orch = IntegratedOrchestrator1076()
        orch.attach_model(model)
        assert orch._model is not None
        assert orch.stethoscope._hook_handle is not None
        orch.stethoscope.detach()

    def test_start_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IntegratedOrchestrator1076(
                dashboard=DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            )
            r = orch.start_cycle()
            assert r["action"] == "CYCLE_START"
            assert r["cycle"] == 1
            assert orch.cycle_count == 1

    def test_process_token_raises_without_model(self):
        orch = IntegratedOrchestrator1076()
        with pytest.raises(RuntimeError):
            orch.process_token("test", token_id=0)

    def test_process_token_with_hidden_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IntegratedOrchestrator1076(
                dashboard=DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            )
            r = orch.process_token("test", token_id=0,
                                    hidden_state=np.array([0.1, 0.2, 0.3]))
            assert r["action"] == "WARMUP"

    def test_process_token_full_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IntegratedOrchestrator1076(
                dashboard=DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            )
            # Need window_size+1 = 4 tokens to exit WARMUP
            hs = [np.array([float(i) * 0.1, float(i) * 0.1 + 0.5]) for i in range(6)]
            results = []
            for i, h in enumerate(hs):
                r = orch.process_token(f"token{i}", token_id=i, hidden_state=h)
                results.append(r)
            assert results[0]["action"] == "WARMUP"
            assert results[1]["action"] == "WARMUP"
            assert results[2]["action"] == "WARMUP"
            # Token 3 has enough history (window_size=3, so 4 snapshots = exit WARMUP)
            assert results[3]["action"] != "WARMUP"

    def test_end_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IntegratedOrchestrator1076(
                dashboard=DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            )
            orch.start_cycle()
            r = orch.end_cycle()
            assert r["action"] == "CYCLE_END"

    def test_get_full_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = IntegratedOrchestrator1076(
                dashboard=DashboardExporter1064(output_dir=tmpdir, buffer_size=10)
            )
            orch.start_cycle()
            orch.process_token("test", token_id=0,
                                hidden_state=np.array([0.1, 0.2]))
            orch.end_cycle()
            r = orch.get_full_report()
            assert r["orchestrator"] == "IntegratedOrchestrator1076"
            assert r["substrate"] == "1076.3"
            assert "vector_theosis" in r
            assert "stethoscope" in r
            assert "sindy" in r
            assert "hamiltonian" in r
            assert "dashboard" in r
            assert "last_10_actions" in r
