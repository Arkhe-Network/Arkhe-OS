import json

import pytest

from substrate_288 import (
    FIPSQuantumTemporalAuditor,
    OrbitalFederatedAutoHealing288,
    QuantumRepeaterRegionalPlanner,
    RetrocausalFiberValidator,
)


@pytest.mark.asyncio
async def test_fiber_validation_runs_in_simulation_without_evidence():
    validator = RetrocausalFiberValidator(seed=42)
    report = await validator.run_e2e_validation(query_count=3)
    assert report["validation_mode"] == "simulation_harness"
    assert not report["physical_backend"]
    assert report["pair_count"] == 8
    assert report["passed_links"] == 8
    assert report["answered_queries"] == 24
    assert len(report["canonical_seal"]) == 64


@pytest.mark.asyncio
async def test_fiber_validation_accepts_physical_evidence_bundle(tmp_path):
    evidence = {
        "physical_backend": True,
        "links": {
            "sa-east-1:us-east-1": {
                "fiber_loss_db": 12.0,
                "qber": 0.02,
                "key_rate_bps": 5000,
            }
        },
    }
    evidence_path = tmp_path / "fiber_evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    validator = RetrocausalFiberValidator(seed=42)
    report = await validator.run_e2e_validation(
        pairs=[("sa-east-1", "us-east-1")],
        evidence_path=str(evidence_path),
        query_count=4,
    )
    assert report["validation_mode"] == "physical_evidence"
    assert report["physical_backend"]
    assert report["results"][0]["physical_backend"]
    assert report["results"][0]["passed"]


@pytest.mark.asyncio
async def test_fiber_validation_marks_bad_evidence_as_failed(tmp_path):
    evidence = {
        "physical_backend": True,
        "links": {
            "sa-east-1:us-east-1": {
                "fiber_loss_db": 80.0,
                "qber": 0.12,
                "key_rate_bps": 10,
            }
        },
    }
    evidence_path = tmp_path / "bad_evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    validator = RetrocausalFiberValidator(seed=42)
    report = await validator.run_e2e_validation(
        pairs=[("sa-east-1", "us-east-1")],
        evidence_path=str(evidence_path),
    )
    assert report["passed_links"] == 0
    assert not report["results"][0]["passed"]


def test_fips_audit_baseline_is_ready():
    auditor = FIPSQuantumTemporalAuditor()
    report = auditor.evaluate(auditor.baseline_evidence())
    assert report["ready_for_lab_submission"]
    assert report["passed_requirements"] == report["total_requirements"]
    assert len(report["canonical_seal"]) == 64


def test_fips_audit_detects_missing_temporal_safety_case():
    auditor = FIPSQuantumTemporalAuditor()
    evidence = auditor.baseline_evidence()
    del evidence["temporal_module_safety_case"]
    report = auditor.evaluate(evidence)
    assert not report["ready_for_lab_submission"]
    assert "temporal_module_safety_case" in report["missing_requirements"]
    assert any(finding["severity"] == "high" for finding in report["findings"])


def test_fips_audit_report_is_json_serializable():
    auditor = FIPSQuantumTemporalAuditor()
    report = auditor.evaluate(auditor.baseline_evidence())
    assert isinstance(json.dumps(report), str)


def test_repeater_expansion_has_twelve_regions():
    planner = QuantumRepeaterRegionalPlanner()
    report = planner.generate_12_region_plan()
    assert report["region_count"] == 12
    assert {"ca-central-1", "eu-central-2", "ap-northeast-3", "ap-southeast-1"}.issubset(report["regions"])
    assert len(report["canonical_seal"]) == 64


def test_repeater_links_keep_segments_under_600_km():
    planner = QuantumRepeaterRegionalPlanner()
    report = planner.generate_12_region_plan()
    assert report["links_requiring_repeaters"] > 0
    assert report["total_repeaters_required"] > 0
    assert report["max_segment_length_km"] <= 600


def test_repeater_plan_for_long_link_requires_repeaters():
    planner = QuantumRepeaterRegionalPlanner()
    plan = planner.plan_link("sa-east-1", "eu-west-1")
    assert plan.distance_km > 600
    assert plan.repeaters_required > 0
    assert plan.segment_length_km <= 600
    assert len(plan.canonical_seal) == 64


def test_repeater_count_for_short_segment_is_zero():
    planner = QuantumRepeaterRegionalPlanner()
    assert planner.repeater_count(500) == 0
    assert planner.repeater_count(601) == 1


def test_substrate_288_reports_are_json_serializable():
    auditor = FIPSQuantumTemporalAuditor()
    audit = auditor.evaluate(auditor.baseline_evidence())
    repeaters = QuantumRepeaterRegionalPlanner().generate_12_region_plan()
    assert isinstance(json.dumps({"audit": audit, "repeaters": repeaters}), str)


def test_orbital_auto_healing_canonical_report_matches_decree():
    report = OrbitalFederatedAutoHealing288().report()
    assert report["tests"]["passed"] == 8
    assert report["tests"]["total"] == 8
    assert report["tests"]["phi_c"] == 1.0
    assert report["canonical_seal"] == "b4f014fd38fa592cf5fc8474a51599f96b2b2437e0df5697d0ed0a4c17397c7a"
    assert len(report["satellites"]) == 5
    assert report["healing"]["successful_actions"] == 5
    assert report["healing"]["retrocausal_actions"] == 2
    assert report["healing"]["orbital_actions"] == 3


def test_orbital_auto_healing_metrics_and_invariants():
    report = OrbitalFederatedAutoHealing288().report()
    assert report["federated_round"]["total_samples"] == 32889
    assert report["federated_round"]["validation_accuracy_avg"] == 0.9097
    assert report["healing"]["avg_phi_c_after"] == 0.9735
    assert report["healing"]["min_phi_c_after"] == 0.9449
    assert report["constitutional_invariants"] == {"ghost": True, "loopseal": True, "gap": True}


def test_unified_282_287_288_report_matches_decree():
    unified = OrbitalFederatedAutoHealing288().unified_report()
    assert unified["tests"] == {"passed": 94, "total": 94}
    assert unified["global_phi_c"] == 1.0
    assert unified["unified_seal"] == "5e9ca1d322177fa231c0ba0c679529214673c5167d1248a47a4a39593e508f1b"
    assert unified["constitutional_invariants"]["ghost"]


def test_orbital_auto_healing_report_json_serializable():
    engine = OrbitalFederatedAutoHealing288()
    assert isinstance(json.dumps({"report": engine.report(), "unified": engine.unified_report()}), str)
