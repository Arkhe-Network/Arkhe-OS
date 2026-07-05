"""Tests for Substrate 394: RUN-COMBINADO Combined Detector."""
import sys
sys.path.insert(0, "substrates/substrate_394")
from substrate_394_run_combinado import CombinedDetector, GHOST
import pytest


class TestCombinedDetector:
    def test_detect_event_structure(self):
        d = CombinedDetector()
        res = d.detect_event("muon")
        assert "particle" in res
        assert "rf" in res
        assert "optico" in res
        assert "combined" in res

    def test_run_simulation(self):
        d = CombinedDetector()
        sim = d.run_simulation(1000)
        assert "results" in sim
        for pt in ["muon", "electron", "photon", "alpha"]:
            assert pt in sim["results"]
            r = sim["results"][pt]
            assert 0 <= r["combined_efficiency"] <= 1

    def test_combined_fpr(self):
        d = CombinedDetector()
        assert d.fpr_rf * d.fpr_optico == 0.0001  # 0.01%

    def test_get_spec(self):
        d = CombinedDetector()
        spec = d.get_spec()
        assert spec["substrate"] == "394-RUN-COMBINADO"
        assert spec["phi_c"] >= GHOST
        assert len(spec["canonical_seal"]) == 64

    def test_heritage(self):
        d = CombinedDetector()
        spec = d.get_spec()
        assert "393-CALIB-REAL" in spec["heritage"]["chain"]

    def test_seal_consistency(self):
        d1 = CombinedDetector()
        d2 = CombinedDetector()
        assert d1.get_spec()["canonical_seal"] == d2.get_spec()["canonical_seal"]
