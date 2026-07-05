"""Tests for Substrate 395: PRIMAKOFF-COMBINADO Hybrid Axion Search."""
import sys
sys.path.insert(0, "substrates/substrate_395")
from substrate_395_primakoff_combinado import PrimakoffCombinado, GHOST
import pytest


class TestPrimakoffCombinado:
    def test_hybrid_sensitivity(self):
        p = PrimakoffCombinado()
        sens = p.compute_hybrid_sensitivity(30)
        assert sens["exposure_days"] == 30
        assert sens["significance_sigma"] > 0
        assert sens["expected_background"] > 0

    def test_sensitivity_scales_with_exposure(self):
        p = PrimakoffCombinado()
        sens_7d = p.compute_hybrid_sensitivity(7)
        sens_30d = p.compute_hybrid_sensitivity(30)
        assert sens_30d["significance_sigma"] > sens_7d["significance_sigma"]

    def test_get_spec(self):
        p = PrimakoffCombinado()
        spec = p.get_spec()
        assert spec["substrate"] == "395-PRIMAKOFF-COMBINADO"
        assert spec["phi_c"] > 0
        assert len(spec["canonical_seal"]) == 64

    def test_heritage_chain(self):
        p = PrimakoffCombinado()
        spec = p.get_spec()
        assert "387-PRIMAKOFF-REAL" in spec["heritage"]["chain"]
        assert "394-RUN-COMBINADO" in spec["heritage"]["chain"]

    def test_veto_efficiency(self):
        p = PrimakoffCombinado()
        assert p.veto_efficiency == 0.99

    def test_agi_agents(self):
        p = PrimakoffCombinado()
        assert p.agi_agents == 16
        assert p.agi_latency_us == 47
