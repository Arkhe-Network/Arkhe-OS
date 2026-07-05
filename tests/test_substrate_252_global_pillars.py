from pathlib import Path

from substrate_252.common_criteria import CommonCriteriaKit, DELIVERABLES
from substrate_252.global_deploy import GlobalAggregatorPlanner


def test_global_aggregator_plan_covers_four_regions_and_bft_bounds():
    planner = GlobalAggregatorPlanner()
    plan = planner.build_plan()

    assert plan.total_nodes == 36
    assert plan.envoy_count == 4
    assert {region.slug for region in plan.regions} == {"na", "eu", "apac", "latam"}
    assert all(region.bft_precondition_ok for region in plan.regions)
    assert plan.canonical_seal


def test_global_aggregator_helm_values_are_renderable():
    planner = GlobalAggregatorPlanner("arkhe/asi:252-global")
    plan = planner.build_plan()
    values = planner.helm_values(plan)

    assert values["globalConsensus"]["protocol"] == "minimmit"
    assert values["globalConsensus"]["coordinator"] == "polaris"
    assert values["regions"][0]["faultTolerance"] == 2
    assert values["image"]["tag"] == "252-global"


def test_common_criteria_kit_writes_seven_deliverables(tmp_path: Path):
    manifest = CommonCriteriaKit().write(tmp_path)

    assert manifest["assurance"] == "EAL4+"
    assert len(manifest["deliverables"]) == 7
    assert len(DELIVERABLES) == 7
    assert (tmp_path / "01-security-target.md").exists()
    assert (tmp_path / "07-vulnerability-analysis.md").exists()
    assert (tmp_path / "manifest.json").exists()


def test_static_global_artifacts_exist():
    root = Path(__file__).resolve().parents[1]
    chart = root / "deploy/kubernetes/arkhe-global-aggregators/Chart.yaml"
    values = root / "deploy/kubernetes/arkhe-global-aggregators/values.yaml"
    compliance = root / "compliance/common-criteria/eal4plus/README.md"

    assert chart.exists()
    assert values.exists()
    assert compliance.exists()
    assert "arkhe-global-aggregators" in chart.read_text(encoding="utf-8")
