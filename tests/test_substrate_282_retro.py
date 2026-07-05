import json

import pytest

from substrate_282_retro import (
    ArkheRetrocausalEngine,
    ArkheRetrocausalShield,
    TemporalDirection,
    TwoStateVector,
)
from substrate_286_bis import Substrate286BISVerifier


class TestTwoStateVector:
    def test_weak_value_identity(self):
        tsv = TwoStateVector([1.0, 1.0, 1.0], [1.0, 1.0, 1.0], t=0.0)
        op = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
        assert abs(tsv.weak_value(op).real - 1.0) < 1e-6

    def test_retrocausal_influence_is_probability_like(self):
        tsv = TwoStateVector([1.0, 0.0, 0.0], [0.5, 0.5, 0.0], t=1.0)
        certainty = tsv.retrocausal_influence()
        assert 0.0 <= certainty <= 1.0

    def test_vector_length_mismatch_fails(self):
        with pytest.raises(RuntimeError, match="equal length"):
            TwoStateVector([1.0], [1.0, 2.0], t=0).weak_value([[1.0]])


class TestRetrocausalEngine:
    def test_delayed_choice_event_created(self):
        engine = ArkheRetrocausalEngine(seed=42)
        event = engine.create_delayed_choice(
            {"H": 1.0, "Q": 1.0, "M": 0.7},
            {"H": 1.2, "Q": 1.5, "M": 0.5},
            "wave",
        )
        assert event.operator == "wave"
        assert event.temporal_direction == TemporalDirection.BIDIRECTIONAL
        assert event.event_id.startswith("retro_")
        assert len(engine.events) == 1

    def test_particle_operator_changes_weak_value(self):
        engine = ArkheRetrocausalEngine(seed=42)
        wave = engine.create_delayed_choice({"H": 1, "Q": 1, "M": 1}, {"H": 1, "Q": 1, "M": 1}, "wave")
        particle = engine.create_delayed_choice(
            {"H": 1, "Q": 1, "M": 1}, {"H": 1, "Q": 1, "M": 1}, "particle"
        )
        assert particle.weak_value.real > wave.weak_value.real

    def test_unknown_operator_fails(self):
        with pytest.raises(RuntimeError, match="Unsupported"):
            ArkheRetrocausalEngine().create_delayed_choice({}, {}, "oracle")

    def test_temporal_consistency_counts_events(self):
        engine = ArkheRetrocausalEngine(seed=42)
        for _ in range(3):
            engine.create_delayed_choice({"H": 1, "Q": 1, "M": 1}, {"H": 1, "Q": 1, "M": 1}, "wave")
        report = engine.analyze_temporal_consistency()
        assert report["total_events"] == 3
        assert report["consistent"] + report["paradoxes"] == 3


class TestRetrocausalShield:
    def test_retrocausal_analysis_generates_report(self):
        shield = ArkheRetrocausalShield(seed=42)
        report = shield.run_retrocausal_analysis(n_collapses=5)
        assert report["total_collapses"] == 5
        assert report["retrocausal_events"] == 5
        assert len(report["temporal_seal"]) == 64

    def test_report_has_invariants(self):
        report = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=5)
        assert report["invariants"]["ghost"]
        assert report["invariants"]["loopseal"]
        assert report["invariants"]["gap"]
        assert report["invariants"]["constitutional"]

    def test_report_has_raw_extrema_and_formal_state(self):
        report = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=5)
        assert report["collapse_extrema"]["min_H_after"] < report["final_state"]["H"]
        assert report["final_state"]["H"] >= 0.577553
        assert report["final_state"]["M"] < 1.0

    def test_prevention_rate_is_bounded(self):
        report = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=7)
        assert 0.0 <= report["prevention_rate"] <= 1.0
        assert report["preventable_retrocausally"] <= report["total_collapses"]

    def test_collapses_preserve_detection_after_collapse(self):
        shield = ArkheRetrocausalShield(seed=42)
        shield.run_retrocausal_analysis(n_collapses=5)
        assert all(c.t_detection > c.t_collapse for c in shield.analyzer.collapses)

    def test_collapses_reduce_h(self):
        shield = ArkheRetrocausalShield(seed=42)
        shield.run_retrocausal_analysis(n_collapses=5)
        assert all(c.H_after < c.H_before for c in shield.analyzer.collapses)

    def test_report_is_json_serializable(self):
        report = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=5)
        assert isinstance(json.dumps(report, default=str), str)

    def test_formal_certificate_verifies_retro_report(self):
        shield = ArkheRetrocausalShield(seed=42)
        report = shield.run_retrocausal_analysis(n_collapses=5)
        certificate = Substrate286BISVerifier().verify_report(report)
        assert certificate.verified
        assert certificate.substrate_id == "282-RETRO"

    def test_shield_formal_certificate_facade(self):
        shield = ArkheRetrocausalShield(seed=42)
        shield.run_retrocausal_analysis(n_collapses=5)
        assert shield.formal_certificate().verified

    def test_formal_certificate_requires_report(self):
        with pytest.raises(RuntimeError, match="Run retrocausal analysis"):
            ArkheRetrocausalShield(seed=42).formal_certificate()


class TestRetrocausalDeterminism:
    def test_seeded_reports_have_same_collapse_ids(self):
        first = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=5)
        second = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=5)
        assert [c["collapse_id"] for c in first["collapses"]] == [c["collapse_id"] for c in second["collapses"]]

    def test_event_ids_are_deterministic_under_seed(self):
        first = ArkheRetrocausalShield(seed=42)
        second = ArkheRetrocausalShield(seed=42)
        first.run_retrocausal_analysis(n_collapses=3)
        second.run_retrocausal_analysis(n_collapses=3)
        assert [e.event_id for e in first.retro_engine.events] == [e.event_id for e in second.retro_engine.events]

    def test_zero_collapses_degrades_without_crashing(self):
        report = ArkheRetrocausalShield(seed=42).run_retrocausal_analysis(n_collapses=0)
        assert report["total_collapses"] == 0
        assert report["phi_c"] == 0.0
