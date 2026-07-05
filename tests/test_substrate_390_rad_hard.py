"""Tests for Substrate 390-RAD-HARD."""
import sys
sys.path.insert(0, "substrates/substrate_390_rad_hard")
from substrate_390_rad_hard import Substrate390RadHard, RadHardSiPM, RadHardFiber
import pytest


class TestRadHardSiPM:
    def test_pde_degradation(self):
        s = RadHardSiPM()
        assert s.pde_after_1yr < s.base_pde
        assert s.pde_after_1yr > 0

    def test_dark_current_increases(self):
        s = RadHardSiPM()
        assert s.dark_current_after_1yr > s.dark_current_increase_per_Mrad


class TestRadHardFiber:
    def test_ria_increases_with_dose(self):
        f = RadHardFiber()
        ria_low = f.compute_ria(100)
        ria_high = f.compute_ria(10000)
        assert ria_high > ria_low


class TestSubstrate390RadHard:
    def test_get_spec(self):
        s = Substrate390RadHard()
        spec = s.get_spec()
        assert spec["substrate"] == "390-RAD-HARD"
        assert len(spec["canonical_seal"]) == 64
        assert "sipm" in spec
        assert "fiber" in spec

    def test_heritage(self):
        s = Substrate390RadHard()
        spec = s.get_spec()
        assert spec["heritage"]["parent"] == "390-OPT"
