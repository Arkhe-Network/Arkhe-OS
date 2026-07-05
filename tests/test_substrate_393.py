"""Tests for Substrate 393: CALIB-REAL Radioactive Calibration."""
import sys, math
sys.path.insert(0, "substrates/substrate_393")
from substrate_393_calib_real import (
    RadioactiveSource, ReferenceScintillator, CalibrationProtocol,
    ExperimentalData, Substrate393CalibVerifier, Severity, ConstitutionalProof,
    GHOST, LOOPSEAL, GAP_SOVEREIGN,
)
import pytest


class TestRadioactiveSource:
    def test_expected_counts(self):
        s = RadioactiveSource()
        ec = s.compute_expected_counts("Am-241", 0.01)
        assert ec > 0
        expected = 3700 * 0.01 * 3600 * 0.852
        assert abs(ec - expected) < 1

    def test_dose_rate(self):
        s = RadioactiveSource()
        dose_am = s.compute_dose_rate_uSv_h("Am-241")
        dose_cs = s.compute_dose_rate_uSv_h("Cs-137")
        assert dose_am == 0.2
        assert dose_cs == 33.0

    def test_unknown_source_dose(self):
        s = RadioactiveSource()
        assert s.compute_dose_rate_uSv_h("Nonexistent") == 0.0

    def test_get_spec(self):
        s = RadioactiveSource()
        spec = s.get_spec()
        assert "Am-241" in spec["sources"]
        assert "Cs-137" in spec["sources"]


class TestReferenceScintillator:
    def test_light_output(self):
        s = ReferenceScintillator()
        assert s.compute_light_output(5.5) == 55000

    def test_detected_signal(self):
        s = ReferenceScintillator()
        sig = s.compute_detected_signal_mV(5.486)
        assert sig > 0

    def test_energy_resolution(self):
        s = ReferenceScintillator()
        res = s.compute_energy_resolution_keV(662)
        assert abs(res - 56.27) < 0.1

    def test_get_spec(self):
        s = ReferenceScintillator()
        spec = s.get_spec()
        assert "EJ-200" in spec["scintillator"]


class TestCalibrationProtocol:
    def test_calibration_curve(self):
        p = CalibrationProtocol()
        result = p.compute_calibration_curve([100, 200], [1000, 2000])
        assert abs(result["slope"] - 0.1) < 1e-10
        assert abs(result["intercept"]) < 1e-10
        assert abs(result["r_squared"] - 1.0) < 1e-10

    def test_efficiency_ratio(self):
        p = CalibrationProtocol()
        assert p.compute_efficiency_ratio(10, 100) == 0.1
        assert p.compute_efficiency_ratio(10, 0) == 0.0


class TestExperimentalData:
    def test_background(self):
        d = ExperimentalData()
        bg = d.generate_background(3600, 10)
        assert bg["total_counts"] == 36000
        assert bg["rate_hz"] == 10

    def test_Am241_data(self):
        d = ExperimentalData()
        data = d.generate_Am241_data(3700, 0.008, 3600)
        assert data["source"] == "Am-241"
        assert data["energy_MeV"] == 5.486
        assert data["observed_counts"] > 0


class TestSubstrate393CalibVerifier:
    def test_platform_hash(self):
        v = Substrate393CalibVerifier()
        h = v.platform_hash()
        assert len(h) == 64

    def test_verification_runs(self):
        v = Substrate393CalibVerifier()
        results = v.run_verification()
        assert len(results) == 6  # 6 modules

    def test_phi_c(self):
        v = Substrate393CalibVerifier()
        v.run_verification()
        phi = v.compute_phi_c()
        assert phi > 0.9
        assert phi <= 1.0

    def test_seal(self):
        v = Substrate393CalibVerifier()
        v.run_verification()
        phi = v.compute_phi_c()
        seal = v.generate_seal(phi)
        assert len(seal) == 64

    def test_proof_validity(self):
        v = Substrate393CalibVerifier()
        results = v.run_verification()
        for r in results:
            for p in r.proofs:
                assert isinstance(p, ConstitutionalProof)
                assert len(p.signature) == 32

    def test_invariants(self):
        assert abs(GHOST - 0.57735) < 1e-4
        assert abs(LOOPSEAL - 0.349066) < 1e-4
        assert GAP_SOVEREIGN == 0.9999
