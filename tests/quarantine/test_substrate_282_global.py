import asyncio
from pathlib import Path

from arkhe_global import (
    AnchoringEvent,
    GlobalRegionOrchestrator,
    RegionRegistry,
    RegionStatus,
    TFQKDDeploymentPlanner,
)


WORKSPACE = Path(__file__).resolve().parents[1]


class TestRegionRegistry:
    def test_default_registry_has_eight_regions(self):
        registry = RegionRegistry()
        assert len(registry.regions) == 8
        assert {"af-south-1", "me-south-1", "ap-south-1"}.issubset(registry.regions)

    def test_region_thresholds_are_adapted(self):
        registry = RegionRegistry()
        assert registry.get_region("eu-west-1").get_phi_c_minimum() == 0.97
        assert registry.get_region("af-south-1").get_phi_c_minimum() == 0.93

    def test_tf_qkd_ready_and_planned_regions(self):
        registry = RegionRegistry()
        ready = [r.region_id for r in registry.get_all_regions() if r.is_tf_qkd_ready()]
        planned = registry.planned_tf_qkd_regions()
        assert len(ready) == 5
        assert planned == ["af-south-1", "me-south-1", "ap-south-1"]

    def test_geodesic_distance_is_symmetric(self):
        registry = RegionRegistry()
        a = registry.calculate_geodesic_distance("sa-east-1", "eu-west-1")
        b = registry.calculate_geodesic_distance("eu-west-1", "sa-east-1")
        assert abs(a - b) < 1e-9
        assert a > 9000

    def test_anchor_selection_for_af_south(self):
        registry = RegionRegistry()
        assert registry.get_primary_anchors_for("af-south-1") == ["sa-east-1", "af-south-1"]
        assert "eu-west-1" in registry.get_secondary_anchors_for("af-south-1")


class TestConsensusAndAnchoring:
    def test_consensus_reaches_with_all_regions(self):
        orchestrator = GlobalRegionOrchestrator()
        state = asyncio.run(orchestrator.run_consensus_round_global())
        assert state.consensus_reached
        assert len(state.participating_regions) == 8
        assert len(state.canonical_seal) == 64

    def test_consensus_fails_when_regions_offline(self):
        orchestrator = GlobalRegionOrchestrator()
        for region in ["sa-east-1", "us-east-1", "eu-west-1", "ap-northeast-1"]:
            orchestrator.region_status[region] = RegionStatus.OFFLINE
        state = asyncio.run(orchestrator.run_consensus_round_global())
        assert not state.consensus_reached
        assert len(state.participating_regions) == 4

    def test_regional_event_below_phi_degrades_region(self):
        orchestrator = GlobalRegionOrchestrator()
        ok = asyncio.run(orchestrator.process_regional_event("af-south-1", "probe", {}, 0.90))
        assert not ok
        assert orchestrator.region_status["af-south-1"] == RegionStatus.DEGRADED

    def test_anchor_flush_returns_batch_seal(self):
        orchestrator = GlobalRegionOrchestrator()
        event = AnchoringEvent("test", "sa-east-1", {"x": 1}, 0.99, 1.0)
        asyncio.run(orchestrator.anchoring.queue_event(event))
        seal = asyncio.run(orchestrator.anchoring.flush_region_anchors("sa-east-1"))
        assert len(seal) == 64
        assert "sa-east-1" not in orchestrator.anchoring.pending_anchors

    def test_global_status_report_has_canonical_seal(self):
        report = GlobalRegionOrchestrator().get_global_status_report()
        assert report["regions_total"] == 8
        assert report["regions_active"] == 8
        assert len(report["canonical_seal"]) == 64


class TestE2ETrafficValidation:
    def test_e2e_traffic_covers_all_ordered_region_pairs(self):
        orchestrator = GlobalRegionOrchestrator()
        report = asyncio.run(orchestrator.run_e2e_traffic_validation(packet_count_per_pair=25))
        assert report["region_count"] == 8
        assert report["pair_count"] == 56
        assert report["total_packets"] == 56 * 25

    def test_e2e_traffic_reaches_consensus_and_anchors(self):
        orchestrator = GlobalRegionOrchestrator()
        report = asyncio.run(orchestrator.run_e2e_traffic_validation(packet_count_per_pair=10))
        assert report["consensus_reached"]
        assert report["anchored_probes"] == 56
        assert len(report["canonical_seal"]) == 64

    def test_e2e_latency_budget_is_reasonable_for_global_mesh(self):
        report = asyncio.run(GlobalRegionOrchestrator().run_e2e_traffic_validation())
        assert report["latency_ms"]["min"] > 0
        assert report["latency_ms"]["avg"] < 150
        assert report["latency_ms"]["max"] < 220

    def test_e2e_results_include_expansion_regions(self):
        report = asyncio.run(GlobalRegionOrchestrator().run_e2e_traffic_validation())
        pairs = {(r["source_region"], r["target_region"]) for r in report["results"]}
        assert ("af-south-1", "me-south-1") in pairs
        assert ("ap-south-1", "ap-southeast-2") in pairs


class TestTFQKDPlanner:
    def test_planner_targets_three_planned_regions(self):
        plan = TFQKDDeploymentPlanner(RegionRegistry()).generate_deployment_plan()
        assert plan["planned_region_count"] == 3
        assert [r["region_id"] for r in plan["regions"]] == ["af-south-1", "me-south-1", "ap-south-1"]

    def test_planner_marks_pilot_region(self):
        plan = TFQKDDeploymentPlanner(RegionRegistry()).generate_deployment_plan()
        ap_south = next(r for r in plan["regions"] if r["region_id"] == "ap-south-1")
        assert ap_south["phase"] == "pilot"
        assert "key_rate_bps" in ap_south["telemetry"]

    def test_each_tf_qkd_region_has_deployment_seal(self):
        plan = TFQKDDeploymentPlanner(RegionRegistry()).generate_deployment_plan()
        assert all(len(region["deployment_seal"]) == 64 for region in plan["regions"])
        assert len(plan["canonical_seal"]) == 64


class TestGlobalArtifacts:
    def test_region_yaml_exists_with_eight_regions(self):
        text = (WORKSPACE / "arkhe-global" / "regions" / "global_region_config.yaml").read_text(encoding="utf-8")
        assert 'canonical_seal: "global282-8regions-canonical-seal-a1b2c3d4e5f6"' in text
        assert "city: São Paulo" in text
        assert "af-south-1:" in text
        assert "ap-southeast-2:" in text
        assert "tf_qkd_backbone: planned_2027" in text

    def test_routing_yaml_exists_with_consensus_policy(self):
        text = (WORKSPACE / "arkhe-global" / "routing" / "global_routing_policy.yaml").read_text(encoding="utf-8")
        assert "weighted_geodesic_phi_c" in text
        assert "threshold_ratio: 0.67" in text
        assert "partition_aware_anchoring" in text

    def test_yaml_loader_uses_config_path_when_available(self):
        registry = RegionRegistry(str(WORKSPACE / "arkhe-global" / "regions" / "global_region_config.yaml"))
        assert len(registry.regions) == 8
        assert registry.get_region("me-south-1").location["country"] == "Bahrain"

    def test_package_exports_global_orchestrator(self):
        import arkhe_global

        assert "GlobalRegionOrchestrator" in arkhe_global.__all__
        assert "TFQKDDeploymentPlanner" in arkhe_global.__all__
