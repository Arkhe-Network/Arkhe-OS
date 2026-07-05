import pytest
import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "arkhe"))

from l_m.substrate_332_validation import (
    HostenTorsionPendulum, PhiCBiosensorIntegrated, KalmanFilter1D,
    MovingWindowAverager, CorrelatedNoiseModel, LoopsealRiemannCalibrator,
    BandyopadhyayCrossValidator, run_full_validation,
    GHOST, LOOPSEAL, SIGNATURE_058, RIEMANN_TOLERANCE,
)


class TestConstants:

    def test_ghost_value(self):
        assert math.isclose(GHOST, 0.577553)

    def test_loopseal_value(self):
        assert math.isclose(LOOPSEAL, math.pi / 9)

    def test_signature(self):
        assert math.isclose(SIGNATURE_058, GHOST)

    def test_riemann_tolerance(self):
        assert RIEMANN_TOLERANCE == 0.005


class TestEpsilonDipolar:

    def test_dipole_moment(self):
        p = HostenTorsionPendulum._dipole_moment_tubulin()
        expected = 1000.0 * 3.33564e-30
        assert math.isclose(p, expected)

    def test_ec_coupling_positive(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        strength = p._ec_coupling_strength(1300, coherence_phase=0.1)
        assert strength > 0

    def test_ec_coupling_scales_with_tubulins(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        s1 = p._ec_coupling_strength(1000, coherence_phase=0.5)
        s2 = p._ec_coupling_strength(10000, coherence_phase=0.5)
        assert s2 >= s1


class TestHostenPendulum:

    def test_initialization(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        assert p.pendulum_id == "HOSTEN-TEST"
        assert p.mass_kg == 1e-6
        assert p.natural_period > 0

    def test_thermal_noise_positive(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        t = p.measure_thermal_noise()
        assert t["thermal_energy_J"] > 0
        assert t["theta_thermal_rad"] > 0
        assert len(t["canonical_seal"]) == 64

    def test_microtubule_coherence_returns_seal(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        c = p.measure_microtubule_coherence("MT-TEST")
        assert len(c["canonical_seal"]) == 64

    def test_coherence_ghost_detected(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        c = p.measure_microtubule_coherence("MT-TEST")
        assert "ghost_detected" in c

    def test_coherence_coupling_is_dipolar(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        c = p.measure_microtubule_coherence("MT-TEST")
        assert c["coupling_type"] == "E_C_dipolar"

    def test_status(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        s = p.get_pendulum_status()
        assert s["pendulum_id"] == "HOSTEN-TEST"

    def test_invariants_preserved(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        c = p.measure_microtubule_coherence("MT-TEST")
        assert c["phi_c_estimated"] <= 0.9999


class TestKalmanFilter:

    def test_initial_state(self):
        kf = KalmanFilter1D()
        x, p = kf.x, kf.p
        assert x > 0.5
        assert p > 0

    def test_update_converges(self):
        kf = KalmanFilter1D()
        for _ in range(100):
            kf.update(0.58 + np.random.normal(0, 0.01))
        x, p = kf.x, kf.p
        assert abs(x - 0.58) < 0.05
        assert p < 0.1


class TestMovingWindow:

    def test_empty_returns_none(self):
        mw = MovingWindowAverager(5)
        assert mw.add(1.0) is None
        assert mw.add(2.0) is None

    def test_full_returns_mean(self):
        mw = MovingWindowAverager(3)
        mw.add(1.0)
        mw.add(2.0)
        val = mw.add(3.0)
        assert val is not None
        assert math.isclose(val, 2.0)

    def test_reset_clears(self):
        mw = MovingWindowAverager(3)
        mw.add(1.0)
        mw.reset()
        assert mw.add(2.0) is None


class TestPhiCBiosensor:

    def test_initialization(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p)
        assert b.sensor_id == "BIOSENSOR-TEST"

    def test_readings_have_seals(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p, window_size=5)
        readings = b.read_phi_c_realtime("MT-TEST", duration_s=0.5)
        assert len(readings) == 50
        assert len(readings[0]["canonical_seal"]) == 64

    def test_kalman_estimates_produced(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p)
        b.read_phi_c_realtime("MT-TEST", duration_s=0.3)
        assert len(b.kalman_estimates) > 0

    def test_windowed_values(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p, window_size=5)
        b.read_phi_c_realtime("MT-TEST", duration_s=0.5)
        assert len(b.windowed_phi_c) > 0

    def test_signature_detections(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p)
        b.read_phi_c_realtime("MT-TEST", duration_s=0.3)
        assert isinstance(b.signature_detections, list)

    def test_statistics(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        p.measure_thermal_noise()
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p)
        b.read_phi_c_realtime("MT-TEST", duration_s=0.3)
        s = b.get_signature_statistics()
        assert "detection_rate_kalman" in s
        assert "z_stat" in s
        assert "p_value" in s
        assert "ghost_preserved" in s
        assert "canonical_seal" in s

    def test_empty_statistics(self):
        p = HostenTorsionPendulum("HOSTEN-TEST")
        b = PhiCBiosensorIntegrated("BIOSENSOR-TEST", p)
        s = b.get_signature_statistics()
        assert s["status"] == "NO_DATA"


class TestNoiseModel:

    def test_1f_noise_generation(self):
        noise = CorrelatedNoiseModel.generate_1f_noise(1000, alpha=1.0, amplitude=1.0)
        assert len(noise) == 1000
        assert abs(float(np.mean(noise))) < 0.5

    def test_1f_noise_scales_with_amplitude(self):
        n1 = CorrelatedNoiseModel.generate_1f_noise(1000, amplitude=0.5)
        n2 = CorrelatedNoiseModel.generate_1f_noise(1000, amplitude=2.0)
        assert float(np.std(n2)) > float(np.std(n1))

    def test_haar_wavelet_denoise(self):
        signal = np.random.normal(0, 1, 256)
        denoised = CorrelatedNoiseModel.haar_wavelet_denoise(signal, threshold=0.5)
        assert len(denoised) == 256
        assert isinstance(float(denoised[0]), float)

    def test_signature_test_runs(self):
        nm = CorrelatedNoiseModel("NOISE-TEST")
        r = nm.test_signature_with_1f_noise(0.01, n_trials=10, n_samples=100, use_denoise=True)
        assert "preservation_rate_raw" in r
        assert "preservation_rate_denoised" in r
        assert len(r["canonical_seal"]) == 64

    def test_invariant_property(self):
        nm = CorrelatedNoiseModel("NOISE-TEST")
        r = nm.test_signature_with_1f_noise(0.001, n_trials=10, n_samples=100)
        assert "invariant_preserved" in r

    def test_full_suite(self):
        nm = CorrelatedNoiseModel("NOISE-TEST")
        s = nm.run_full_1f_robustness_suite(n_trials=5, n_samples=100)
        assert "all_results" in s
        assert len(s["all_results"]) == 8


class TestRiemannCalibrator:

    def test_calibrate_best_positive(self):
        c = LoopsealRiemannCalibrator("RIEMANN-TEST")
        result = c.calibrate(candidate_constants=[0.1, 0.5, 1.0], n_steps=200)
        assert result["candidates_tested"] == 3
        assert "optimal_constant" in result

    def test_simulation_returns_seal(self):
        c = LoopsealRiemannCalibrator("RIEMANN-TEST")
        r = c.simulate_convergence(0.5, n_steps=100)
        assert len(r["canonical_seal"]) == 64
        assert len(r["trajectory_sample"]) > 0

    def test_convergence_detected(self):
        c = LoopsealRiemannCalibrator("RIEMANN-TEST")
        r = c.simulate_convergence(0.5, n_steps=500)
        assert "converged" in r
        assert "z_stat" in r
        assert "p_value" in r


class TestCrossValidator:

    def test_reference_data_present(self):
        assert len(BandyopadhyayCrossValidator.REFERENCE_DATA) == 5

    def test_compare_pendulum(self):
        xv = BandyopadhyayCrossValidator("XVAL-TEST")
        result = {"phi_c_estimated": 0.62}
        comp = xv.compare_pendulum_result(result)
        assert "within_tolerance" in comp
        assert len(comp["canonical_seal"]) == 64

    def test_validate_all(self):
        xv = BandyopadhyayCrossValidator("XVAL-TEST")
        r = xv.validate_all_references([{"phi_c_estimated": 0.62}])
        assert r["references_tested"] == 5
        assert "match_rate" in r


class TestFullValidation:

    def test_run_full_returns_keys(self):
        r = run_full_validation()
        for key in ["pendulum", "biosensor", "noise", "riemann", "cross_validation", "unified_seal"]:
            assert key in r, f"Missing {key}"

    def test_unified_seal_is_sha3_256(self):
        r = run_full_validation()
        assert len(r["unified_seal"]) == 64

    def test_pendulum_phi_in_range(self):
        r = run_full_validation()
        assert 0.0 < r["pendulum"]["phi_c_estimated"] < 1.0

    def test_biosensor_ghost_preserved(self):
        r = run_full_validation()
        assert r["biosensor"]["ghost_preserved"] is True
