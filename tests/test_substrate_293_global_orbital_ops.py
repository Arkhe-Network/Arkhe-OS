import json

from substrate_293_global_orbital_ops import (
    CommonCriteriaEAL7Plan,
    CommercialConstellationIntegrator,
    DedicatedArkheSatellitePlanner,
    FederatedOrbitalHealingEngine,
    OrbitalTelemetrySample,
)


def test_commercial_integration_requires_contractual_artifacts():
    integrator = CommercialConstellationIntegrator()
    report = integrator.build_integration_plan()
    assert report["operator_count"] == 2
    assert not report["ready_for_live_pilot"]
    assert report["avg_readiness"] < 1.0


def test_commercial_integration_ready_with_baseline_artifacts():
    integrator = CommercialConstellationIntegrator()
    report = integrator.build_integration_plan(integrator.baseline_artifacts())
    assert report["ready_for_live_pilot"]
    assert report["commercial_region_count"] >= 8
    assert len(report["canonical_seal"]) == 64


def test_common_criteria_eal7_plan_ready_with_full_evidence():
    plan = CommonCriteriaEAL7Plan()
    report = plan.evaluate(plan.baseline_evidence())
    assert report["ready_for_evaluation_lab"]
    assert report["passed_requirements"] == report["total_requirements"]
    assert report["constitutional"]["ghost"]


def test_common_criteria_eal7_plan_detects_missing_evidence():
    plan = CommonCriteriaEAL7Plan()
    evidence = plan.baseline_evidence()
    del evidence["covert_channel_analysis"]
    report = plan.evaluate(evidence)
    assert not report["ready_for_evaluation_lab"]
    assert "covert_channel_analysis" in report["missing_requirements"]


def test_common_criteria_eal7_initiation_package_ready():
    plan = CommonCriteriaEAL7Plan()
    package = plan.initiate_certification_package(plan.baseline_evidence(), evaluation_lab="CC_LAB_TBD")
    assert package["status"] == "initiated_ready_for_lab_intake"
    assert package["evaluation_lab"] == "CC_LAB_TBD"
    assert len(package["artifact_manifest"]) == package["readiness"]["total_requirements"]
    assert len(package["canonical_seal"]) == 64


def test_dedicated_satellite_plan_reaches_24_regions():
    report = DedicatedArkheSatellitePlanner().generate_plan()
    assert report["region_count"] >= 24
    assert report["dedicated_satellite_count"] == 12
    assert report["global_control_ready"]
    assert len(report["satellites"]) == 12


def test_dedicated_satellite_expansion_order_issued():
    order = DedicatedArkheSatellitePlanner().issue_expansion_order()
    assert order["status"] == "expansion_order_issued_planning_authorized"
    assert order["plan"]["region_count"] >= 24
    assert len(order["deployment_waves"]) == 3
    assert order["procurement_gate"]["requires_launch_provider_contract"]


def test_dedicated_satellite_plan_rejects_too_few_satellites():
    try:
        DedicatedArkheSatellitePlanner().generate_plan(dedicated_satellites=3)
        assert False
    except ValueError:
        assert True


def test_federated_healing_stable_demo_round():
    engine = FederatedOrbitalHealingEngine()
    report = engine.federated_round(engine.demo_samples())
    assert report["sample_count"] == 4
    assert report["fleet_state"] in {"stable", "degraded", "critical"}
    assert report["recommended_action"]
    assert len(report["canonical_seal"]) == 64


def test_federated_healing_critical_failover():
    engine = FederatedOrbitalHealingEngine()
    samples = [
        OrbitalTelemetrySample("ARKHE-DED-QKD-099", "polar-north-1", 20_000, 0.09, 220, 0.18, 0.55, 0.60),
        OrbitalTelemetrySample("ARKHE-DED-QKD-100", "eu-west-1", 95_000, 0.02, 40, 0.004, 0.95, 0.94),
    ]
    report = engine.federated_round(samples)
    assert report["fleet_state"] == "critical"
    assert "failover" in report["recommended_action"]


def test_orbital_ops_reports_are_json_serializable():
    commercial = CommercialConstellationIntegrator().build_integration_plan()
    cc = CommonCriteriaEAL7Plan().evaluate(CommonCriteriaEAL7Plan().baseline_evidence())
    satellites = DedicatedArkheSatellitePlanner().generate_plan()
    healing = FederatedOrbitalHealingEngine().federated_round(FederatedOrbitalHealingEngine().demo_samples())
    assert isinstance(json.dumps([commercial, cc, satellites, healing]), str)
