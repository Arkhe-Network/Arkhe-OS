import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "arkhe"))

from l_m.cannabis_triad import (
    CannabisTriad, TrichomeExpressionEvent, BiosensorSample, PdtCSession,
    GHOST, GAP_MAX, LOOPSEAL, PHI, ALPHA_INV, run_full_demonstration,
)


class TestInvariants:

    def test_ghost_is_sqrt3_over_3(self):
        assert math.isclose(GHOST, math.sqrt(3) / 3)

    def test_loopseal_is_pi_over_9(self):
        assert math.isclose(LOOPSEAL, math.pi / 9)

    def test_phi_is_golden_ratio(self):
        assert math.isclose(PHI, (1 + math.sqrt(5)) / 2)

    def test_alpha_inv(self):
        assert math.isclose(ALPHA_INV, 137.035999084)


class TestCannabisTriadReporter:

    def test_initial_phi_zero(self):
        triad = CannabisTriad()
        assert triad.reporter_phi == 0.0

    def test_express_increases_cannabinoids(self):
        triad = CannabisTriad()
        triad.trichome_density_mm2 = 0.003
        triad.express_promoter("THC_synthase_promoter", 0.7480)
        assert math.isclose(triad.cannabinoids["THC"], 0.00748)

    def test_express_generates_seal(self):
        triad = CannabisTriad()
        event = triad.express_promoter("CBD_synthase_promoter", 0.5)
        assert len(event.seal) == 64

    def test_express_appends_event(self):
        triad = CannabisTriad()
        triad.express_promoter("CBG_synthase_promoter", 0.5)
        assert len(triad.events) == 1

    def test_phi_c_increases_with_events(self):
        triad = CannabisTriad()
        triad.trichome_density_mm2 = 0.003
        before = triad.reporter_phi
        triad.express_promoter("THC_synthase_promoter", 0.7480)
        triad.express_promoter("THC_synthase_promoter", 0.6160)
        triad.express_promoter("THC_synthase_promoter", 0.8)
        assert triad.reporter_phi > before

    def test_fixed_demo_matches_validation(self):
        triad = CannabisTriad()
        triad.run_full_demonstration()
        assert len(triad.events) == 5
        assert math.isclose(triad.cannabinoids["THC"], 0.01364, abs_tol=0.0001)
        assert math.isclose(triad.cannabinoids["CBD"], 0.01584, abs_tol=0.0001)
        assert math.isclose(triad.cannabinoids["CBG"], 0.00396, abs_tol=0.0001)
        assert math.isclose(triad.trichome_density_mm2, 0.0033)

    def test_reporter_phi_below_ghost_in_seedling(self):
        triad = CannabisTriad()
        triad.run_full_demonstration()
        assert triad.reporter_phi < GHOST


class TestCannabisTriadBiosensor:

    def test_detection_below_limit(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-001", 45.0)
        assert sample.detected is False
        assert sample.risk == "NEGATIVE"

    def test_detection_above_limit(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-002", 150.0)
        assert sample.detected is True
        assert sample.risk == "POSITIVE"

    def test_critical_with_scras(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-003", 80.0, ["5F-ADB"])
        assert sample.risk == "CRITICAL"

    def test_critical_high_thc_with_scras(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-004", 500.0, ["JWH-018", "AM-2201"])
        assert sample.risk == "CRITICAL"
        assert len(sample.scras) == 2

    def test_phi_c_preserved(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-005", 150.0)
        assert sample.phi_c >= GHOST

    def test_phi_c_drops_with_scras(self):
        triad = CannabisTriad()
        clean = triad.analyze_sample("CLEAN", 150.0)
        dirty = triad.analyze_sample("DIRTY", 150.0, ["JWH-018"])
        assert dirty.phi_c < clean.phi_c

    def test_sample_generates_seal(self):
        triad = CannabisTriad()
        sample = triad.analyze_sample("T-SEAL", 150.0)
        assert len(sample.seal) == 64

    def test_full_demo_samples(self):
        triad = CannabisTriad()
        triad.run_full_demonstration()
        assert len(triad.samples) == 5
        assert triad.total_scra_alerts == 3

    def test_alert_rate(self):
        triad = CannabisTriad()
        assert triad.alert_rate() == 0.0
        triad.analyze_sample("T-001", 500.0, ["JWH-018"])
        assert triad.alert_rate() == 1.0
        triad.analyze_sample("T-002", 45.0)
        assert triad.alert_rate() == 0.5


class TestCannabisTriadPDTC:

    def test_therapy_reduces_volume(self):
        triad = CannabisTriad()
        session = triad.apply_pdtc("T-001", 50, 10.0, 250)
        assert session.final_volume_mm3 < session.initial_volume_mm3

    def test_efficacy_positive(self):
        triad = CannabisTriad()
        session = triad.apply_pdtc("T-001", 50, 10.0, 250)
        assert session.efficacy_pct > 0.0

    def test_generates_seal(self):
        triad = CannabisTriad()
        session = triad.apply_pdtc("T-001", 50, 10.0, 250)
        assert len(session.seal) == 64

    def test_higher_dose_increases_damage(self):
        triad = CannabisTriad()
        low = triad.apply_pdtc("T-001", 30, 8.0, 150)
        high = triad.apply_pdtc("T-002", 75, 12.0, 400)
        assert high.total_damage > low.total_damage

    def test_synergy_above_mono(self):
        ros_only = CannabisTriad().apply_pdtc("T-ROS", 0, 10.0, 250)
        combo = CannabisTriad().apply_pdtc("T-COMBO", 50, 10.0, 250)
        assert combo.efficacy_pct > ros_only.efficacy_pct

    def test_average_efficacy(self):
        triad = CannabisTriad()
        triad.apply_pdtc("T-001", 50, 10.0, 250)
        triad.apply_pdtc("T-002", 75, 12.0, 400)
        assert triad.average_efficacy() > 0.0

    def test_pdtc_phi_from_sessions(self):
        triad = CannabisTriad()
        assert triad.pdtc_phi == 0.0
        triad.apply_pdtc("T-001", 50, 10.0, 250)
        assert triad.pdtc_phi > 0.0

    def test_full_demo_matches_validation(self):
        triad = CannabisTriad()
        triad.run_full_demonstration()
        assert len(triad.sessions) == 4
        efficacy = triad.average_efficacy()
        assert 17.0 <= efficacy <= 20.0

    def test_volume_reduction_property(self):
        session = CannabisTriad().apply_pdtc("T-001", 50, 10.0, 250)
        assert session.volume_reduction_pct > 0.0

    def test_efficacy_values(self):
        triad = CannabisTriad()
        s1 = triad.apply_pdtc("T-001", 50, 10.0, 250)
        s2 = triad.apply_pdtc("T-001", 50, 15.0, 250)
        assert math.isclose(s1.efficacy_pct, 15.65, abs_tol=0.02)
        assert math.isclose(s2.efficacy_pct, 22.93, abs_tol=0.02)

    def test_pdtc_nonlinear_saturation(self):
        triad = CannabisTriad()
        huge = triad.apply_pdtc("T-HUGE", 500, 100.0, 50)
        assert huge.efficacy_pct <= 99.99


class TestCanonicalSeal:

    def test_canonical_seal_is_sha3_256(self):
        triad = CannabisTriad()
        seal = triad.canonical_seal_hash()
        assert len(seal) == 64

    def test_deterministic_seal(self):
        t1 = CannabisTriad()
        t1.run_full_demonstration()
        t2 = CannabisTriad()
        t2.run_full_demonstration()
        assert t1.canonical_seal_hash() == t2.canonical_seal_hash()


class TestFullDemonstration:

    def test_all_components_present(self):
        result = run_full_demonstration()
        assert "reporter" in result
        assert "biosensor" in result
        assert "pdtc" in result

    def test_triad_seal_present(self):
        result = run_full_demonstration()
        assert len(result["triad_seal"]) == 64

    def test_invariants_checked(self):
        result = run_full_demonstration()
        iv = result["invariants"]
        assert "reporter_above_ghost" in iv
        assert "sensor_above_ghost" in iv
        assert "pdtc_above_ghost" in iv
        assert iv["sensor_above_ghost"] is True
        assert math.isclose(iv["ghost_value"], GHOST)
        assert math.isclose(iv["phi_value"], PHI)
        assert math.isclose(iv["alpha_inv_value"], ALPHA_INV)

    def test_triad_seal_is_sha3_256(self):
        result = run_full_demonstration()
        assert len(result["triad_seal"]) == 64


class TestDataClasses:

    def test_trichome_event_seal(self):
        e = TrichomeExpressionEvent(
            event_id="EVENT-0001", promoter="THC_synthase_promoter",
            transcription_activity=0.5, photons_emitted=528.0, cannabinoid_delta=0.005,
        )
        assert len(e.seal) == 64

    def test_biosensor_sample_seal(self):
        s = BiosensorSample(
            sample_id="S-001", thc_pM=150.0,
            detected=True, risk="POSITIVE", scras=[], phi_c=0.78,
        )
        assert len(s.seal) == 64

    def test_pdtc_session_seal(self):
        s = PdtCSession(
            session_id="PDTC-0001", tumor_id="T-001",
            cbd_ug=50, ir_j_cm2=10.0, initial_volume_mm3=250,
            final_volume_mm3=210.88, efficacy_pct=15.65, total_damage=2.4744,
        )
        assert len(s.seal) == 64

    def test_volume_reduction(self):
        s = PdtCSession(
            session_id="PDTC-0001", tumor_id="T-001",
            cbd_ug=50, ir_j_cm2=10.0, initial_volume_mm3=250,
            final_volume_mm3=210.88, efficacy_pct=15.65, total_damage=2.4744,
        )
        assert s.volume_reduction_pct > 0.0

    def test_default_seal_generated(self):
        e = TrichomeExpressionEvent(
            event_id="EVENT-T", promoter="THC_synthase_promoter",
            transcription_activity=0.5, photons_emitted=528.0, cannabinoid_delta=0.005,
        )
        assert len(e.seal) == 64

    def test_explicit_seal_kept(self):
        e = TrichomeExpressionEvent(
            event_id="EVENT-E", promoter="THC_synthase_promoter",
            transcription_activity=0.5, photons_emitted=528.0,
            cannabinoid_delta=0.005, seal="custom-seal",
        )
        assert e.seal == "custom-seal"
