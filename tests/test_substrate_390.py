"""Tests for Substrate 390: RuView-RAD Particle Detector."""
import sys, math
sys.path.insert(0, "substrates/substrate_390")
from ruview_rad import (
    RuViewRADDetector, ParticleClassifier, CherenkovEvent,
    ParticleType, DAQConfig, GHOST,
)
import pytest


class TestParticleClassifier:
    def test_muon(self):
        ptype, e, c = ParticleClassifier.classify(4000, 60000)
        assert ptype == ParticleType.MUON
        assert e > 1000

    def test_electron(self):
        ptype, e, c = ParticleClassifier.classify(2500, 15000)
        assert ptype == ParticleType.ELECTRON

    def test_alpha(self):
        ptype, e, c = ParticleClassifier.classify(1000, 8000)
        assert ptype == ParticleType.ALPHA

    def test_photon(self):
        ptype, e, c = ParticleClassifier.classify(200, 500)
        assert ptype == ParticleType.PHOTON

    def test_unknown(self):
        ptype, e, c = ParticleClassifier.classify(50, 5)
        assert ptype == ParticleType.UNKNOWN

    def test_from_event_muon(self):
        ev = CherenkovEvent(1000, 4000, 60000)
        ParticleClassifier.from_event(ev)
        assert ev.particle_type == ParticleType.MUON


class TestRuViewRADDetector:
    def test_initialization(self):
        d = RuViewRADDetector()
        assert d.state.value == "idle"
        assert d.total_events == 0

    def test_arm(self):
        d = RuViewRADDetector()
        seal = d.arm()
        assert d.state.value == "acquiring"
        assert len(seal) == 64

    def test_ingest_event(self):
        d = RuViewRADDetector()
        d.arm()
        ev = d.ingest_event(4000, 60000)
        assert ev.particle_type == ParticleType.MUON
        assert d.total_events == 1

    def test_readout(self):
        d = RuViewRADDetector()
        d.arm()
        d.ingest_event(4000, 60000)
        d.ingest_event(200, 500)
        result = d.readout()
        assert result["total"] == 2
        assert result["muon"] == 1
        assert d.state.value == "idle"

    def test_rate_hz(self):
        d = RuViewRADDetector()
        d.arm()
        assert d.rate_hz == 0.0
        d.ingest_event(4000, 60000)
        assert d.rate_hz > 0

    def test_reset(self):
        d = RuViewRADDetector()
        d.arm()
        d.ingest_event(4000, 60000)
        d.reset()
        assert d.total_events == 0

    def test_phi_c(self):
        d = RuViewRADDetector()
        assert d.phi_c == GHOST
        d.arm()
        d.ingest_event(4000, 60000)  # classified
        assert d.phi_c > GHOST

    def test_stats(self):
        d = RuViewRADDetector()
        s = d.stats
        assert "state" in s

    def test_canonical_seal(self):
        d = RuViewRADDetector()
        assert len(d.canonical_seal()) == 64

    def test_config_custom(self):
        cfg = DAQConfig(adc_freq_hz=500_000_000, threshold_adc=300)
        d = RuViewRADDetector(cfg)
        assert d.config.adc_freq_hz == 500_000_000

    def test_ingest_multiple_types(self):
        d = RuViewRADDetector()
        d.arm()
        d.ingest_event(4000, 60000)  # muon
        d.ingest_event(2500, 15000)  # electron
        d.ingest_event(1000, 8000)   # alpha
        d.ingest_event(200, 500)     # photon
        d.ingest_event(50, 5)        # unknown
        assert d.total_events == 5
        result = d.readout()
        assert result["muon"] == 1
        assert result["electron"] == 1
        assert result["alpha"] == 1
        assert result["photon"] == 1
        assert result["unknown"] == 1
