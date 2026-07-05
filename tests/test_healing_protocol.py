import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "arkhe"))

from l_m.healing_protocol import (
    HealingEngine, HealingProtocol, HealingSession, BiologicalTarget,
    BiophotonSource, ProtocolType, GHOST, GAP_MAX, PHI,
)


class TestHealingProtocol:

    def test_protocol_definitions_exist(self):
        protocols = HealingProtocol.standard_protocols()
        assert len(protocols) == 4
        for pt in ProtocolType:
            assert pt in protocols

    def test_severe_deficit_longer_duration(self):
        severe = HealingProtocol.standard_protocols()[ProtocolType.SEVERE_DEFICIT]
        maintenance = HealingProtocol.standard_protocols()[ProtocolType.MAINTENANCE]
        assert severe.base_duration_s > maintenance.base_duration_s

    def test_effective_duration_increases_with_lower_phi(self):
        protocol = HealingProtocol.standard_protocols()[ProtocolType.CRITICAL_DEFICIT]
        low_phi = protocol.effective_duration(0.40)
        high_phi = protocol.effective_duration(0.60)
        assert low_phi > high_phi


class TestBiophotonSource:

    def test_calibrated_flux_positive(self):
        source = BiophotonSource.calibrated_for_healing()
        assert source.photon_flux > 0

    def test_emit_photons_returns_positive(self):
        source = BiophotonSource(photon_flux=77000)
        count = source.emit_photons(1.0)
        assert count == 77000

    def test_emit_accumulates(self):
        source = BiophotonSource(photon_flux=1000)
        source.emit_photons(5.0)
        assert source._total_emitted == 5000


class TestBiologicalTarget:

    def test_severity_classification(self):
        targets = BiologicalTarget.standard_targets()
        assert len(targets) == 4
        assert targets[0].severity_class() == ProtocolType.CRITICAL_DEFICIT
        assert targets[1].severity_class() == ProtocolType.MODERATE_DEFICIT
        assert targets[2].severity_class() == ProtocolType.SEVERE_DEFICIT
        assert targets[3].severity_class() == ProtocolType.MAINTENANCE

    def test_phi_c_bounded(self):
        target = BiologicalTarget("T-001", 0.50)
        assert 0.0 <= target.phi_c_current <= GAP_MAX


class TestHealingSession:

    def test_session_generates_seal(self):
        target = BiologicalTarget("T-001", 0.50)
        protocol = HealingProtocol.standard_protocols()[ProtocolType.CRITICAL_DEFICIT]
        session = HealingSession(
            session_id="TEST-001",
            target=target,
            protocol=protocol,
            phi_c_before=0.50,
            phi_c_after=0.55,
            photons_emitted=1e6,
            duration_s=60.0,
            efficiency=5e-8,
        )
        assert len(session.seal) == 64
        assert math.isclose(session.delta_phi_c(), 0.05)

    def test_delta_phi_positive(self):
        target = BiologicalTarget("T-001", 0.50)
        protocol = HealingProtocol.standard_protocols()[ProtocolType.CRITICAL_DEFICIT]
        session = HealingSession(
            session_id="TEST-002",
            target=target,
            protocol=protocol,
            phi_c_before=0.50,
            phi_c_after=0.55,
            photons_emitted=1e6,
            duration_s=60.0,
            efficiency=5e-8,
        )
        assert session.delta_phi_c() > 0


class TestHealingEngine:

    def test_engine_initializes(self):
        engine = HealingEngine()
        assert engine.photon_source is not None
        assert len(engine.protocols) == 4

    def test_apply_therapy_increases_phi(self):
        engine = HealingEngine()
        target = BiologicalTarget("TEST-CEL", 0.50)
        session = engine.apply_therapy(target)
        assert session.phi_c_after > session.phi_c_before
        assert target.phi_c_current > 0.50

    def test_apply_therapy_generates_seal(self):
        engine = HealingEngine()
        session = engine.apply_therapy(BiologicalTarget("TEST-CEL", 0.50))
        assert len(session.seal) == 64

    def test_apply_therapy_records_session(self):
        engine = HealingEngine()
        engine.apply_therapy(BiologicalTarget("T1", 0.50))
        assert len(engine.sessions) == 1

    def test_clinical_trial_runs_all_targets(self):
        engine = HealingEngine()
        results = engine.run_clinical_trial(BiologicalTarget.standard_targets())
        assert len(results) == 4

    def test_clinical_trial_increases_all_phi(self):
        engine = HealingEngine()
        for r in engine.run_clinical_trial():
            assert r.phi_c_after > r.phi_c_before

    def test_clinical_trial_severity_matches_duration(self):
        engine = HealingEngine()
        results = engine.run_clinical_trial()
        assert results[2].duration_s >= results[3].duration_s

    def test_report_contains_all_metrics(self):
        engine = HealingEngine()
        engine.run_clinical_trial()
        report = engine.generate_trial_report()
        assert report["total_sessions"] == 4
        assert "total_photons_emitted" in report
        assert "total_phi_c_restored" in report
        assert "average_efficiency" in report
        assert "invariants" in report
        assert "unified_conformity_seal" in report

    def test_invariants_are_preserved(self):
        engine = HealingEngine()
        engine.run_clinical_trial()
        iv = engine.generate_trial_report()["invariants"]
        assert iv["ghost"] is True
        assert iv["gap"] is True
        assert iv["loopseal"] is True

    def test_efficiency_matches_eta_base_with_golden_boost(self):
        engine = HealingEngine()
        session = engine.apply_therapy(BiologicalTarget("T-001", 0.50))
        expected_eta = 8.8e-9 * (1.0 + 0.1 * PHI)
        assert math.isclose(session.efficiency, expected_eta, rel_tol=1e-12)

    def test_many_sessions_accumulate_photons(self):
        engine = HealingEngine()
        target = BiologicalTarget("T-ACCUM", 0.50)
        for _ in range(5):
            engine.apply_therapy(target)
        assert engine._total_photons_emitted > 0
        assert len(engine.sessions) == 5

    def test_photons_scale_with_duration(self):
        engine = HealingEngine()
        t1 = engine.apply_therapy(BiologicalTarget("T-SHORT", 0.50))
        t2 = engine.apply_therapy(BiologicalTarget("T-LONG", 0.40))
        assert t2.photons_emitted > t1.photons_emitted
