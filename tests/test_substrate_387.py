"""Tests for Substrate 387: PRIMAKOFF-REAL Axion Search."""
import sys, math
sys.path.insert(0, "substrates/substrate_387")
from substrate_387_primakoff_real import PrimakoffReal, PHI
import pytest


class TestPrimakoffReal:
    def test_conversion_volume(self):
        p = PrimakoffReal()
        v = p.compute_conversion_volume()
        assert v > 0
        assert v < 1  # ~0.017 m^3

    def test_sensitivity(self):
        p = PrimakoffReal()
        sens = p.compute_sensitivity(7)
        assert sens["background_raw"] == 3.5
        assert sens["background_vetoed"] < sens["background_raw"]
        assert sens["significance_sigma"] > 0

    def test_calibration_coefficients(self):
        p = PrimakoffReal()
        cal = p.compute_calibration_coefficients()
        assert cal["efficiency_RuView_alpha"] == 0.008
        assert cal["efficiency_RuView_gamma"] == 0.012
        assert cal["calibration_slope_keV_per_mV"] == 4.5

    def test_get_spec_structure(self):
        p = PrimakoffReal()
        spec = p.get_spec()
        assert spec["substrate"] == "387-PRIMAKOFF-REAL"
        assert "coil" in spec
        assert "detector_primary" in spec
        assert "detector_veto" in spec
        assert "calibration_coefficients" in spec

    def test_heritage_chain(self):
        p = PrimakoffReal()
        spec = p.get_spec()
        assert "393-CALIB-REAL" in spec["heritage"]["chain"]

    def test_phi_constant(self):
        assert abs(PHI - 1.61803) < 1e-4
