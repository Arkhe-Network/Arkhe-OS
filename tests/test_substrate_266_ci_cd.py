from pathlib import Path

import pytest

from substrate_255 import ArkheCoreImageBuilder, BuildStage
from substrate_266 import ArkheCICDPipeline, ArkheMultiArchBuilder, SUPPORTED_TARGETS, build_all_arch


ROOT = Path(__file__).resolve().parents[1]


def test_build_all_arch_generates_manifest(tmp_path):
    manifest = build_all_arch(SUPPORTED_TARGETS, tmp_path)

    assert manifest["substrate"] == 266
    assert manifest["targets"] == ["arm64", "amd64", "riscv64", "loongarch64", "s390x"]
    assert len(manifest["canonical_seal"]) == 64
    for arch in SUPPORTED_TARGETS:
        assert arch in manifest["reports"]
        assert manifest["reports"][arch]["uc26"]["release_date"] == "2026-05-14"
        assert manifest["reports"][arch]["uc26"]["base_composition"] == "chisel"
        assert manifest["reports"][arch]["architecture_profile"]["supported"] is True
        assert (tmp_path / f"arkhe-core-{arch}-build-report.json").exists()
    assert (tmp_path / "arkhe-core-build-manifest.json").exists()


def test_build_all_arch_accepts_x86_64_alias(tmp_path):
    manifest = build_all_arch(["x86_64"], tmp_path)
    assert manifest["targets"] == ["amd64"]
    assert manifest["reports"]["amd64"]["model_name"] == "arkhe-core-26-amd64"


def test_workflow_declares_multi_arch_matrix():
    workflow = ROOT / ".github" / "workflows" / "arkhe-core-build.yml"
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "arm64" in text
    assert "x86_64" in text or "amd64" in text
    assert "riscv64" in text
    assert "loongarch64" in text
    assert "s390x" in text
    assert "ubuntu_core_builder_test_suite.py" in text
    assert "global_mesh_asi_tpi_test_suite.py" in text


def test_cicd_pipeline_lifecycle_success():
    builder = ArkheCoreImageBuilder()
    cicd = ArkheCICDPipeline(builder)
    pipeline = cicd.create_pipeline(trigger="push", branch="main")

    assert pipeline.pipeline_id
    assert len(pipeline.pipeline_id) == 16
    assert len(pipeline.stages) == 5
    assert len(pipeline.canonical_seal) == 64
    assert "matrix" in pipeline.yaml_manifest
    assert "remote-build" in pipeline.yaml_manifest
    assert "trivy" in pipeline.yaml_manifest.lower()
    assert builder._stage_log[-1]["stage"] == BuildStage.CI_CD_PIPELINE.value

    for stage in pipeline.stages:
        cicd.execute_stage(stage.name, success=True, duration_ms=250, artifacts=[f"{stage.name}.json"])

    report = cicd.get_pipeline_report()
    assert report["overall_status"] == "success"
    assert all(stage["status"] == "success" for stage in report["stages"])
    assert report["yaml_manifest_length"] > 1000


def test_cicd_pipeline_failure_and_errors():
    cicd = ArkheCICDPipeline(ArkheCoreImageBuilder())
    assert cicd.get_pipeline_report()["error"] == "No pipeline created"
    with pytest.raises(RuntimeError, match="not created"):
        cicd.execute_stage("checkout")

    cicd.create_pipeline(trigger="pull_request", branch="feature/test")
    cicd.execute_stage("checkout", success=True)
    cicd.execute_stage("lint-and-test", success=False)
    assert cicd.get_pipeline_report()["overall_status"] == "failure"
    with pytest.raises(RuntimeError, match="not found"):
        cicd.execute_stage("missing")


def test_multi_arch_profiles_and_default_builds():
    builder = ArkheCoreImageBuilder()
    multi = ArkheMultiArchBuilder(builder)
    mab = multi.create_multi_arch_build()

    assert [profile.name for profile in mab.architectures] == ["arm64", "amd64", "riscv64", "loongarch64", "s390x"]
    assert len(mab.canonical_seal) == 64
    assert builder._stage_log[-1]["stage"] == BuildStage.MULTI_ARCH_BUILD.value
    assert multi.ARCHITECTURE_PROFILES["arm64"].gadget_snap == "pi"
    assert multi.ARCHITECTURE_PROFILES["amd64"].kernel_snap == "pc-kernel"
    assert multi.ARCHITECTURE_PROFILES["riscv64"].target_device == "generic-riscv64"
    assert multi.ARCHITECTURE_PROFILES["loongarch64"].target_device == "generic-loongarch64"
    assert multi.ARCHITECTURE_PROFILES["s390x"].target_device == "ibm-z-mainframe"

    for arch in ["arm64", "amd64", "riscv64", "loongarch64", "s390x"]:
        image = multi.build_for_architecture(arch)
        assert image.model_assertion.model_name == f"arkhe-core-26-{arch}"
        assert image.tpm_seal is not None
        assert all(image.constitutional_principles.values())

    report = multi.get_multi_arch_report()
    assert report["builds_completed"] == ["arm64", "amd64", "riscv64", "loongarch64", "s390x"]
    assert report["remote_build_enabled"] is True
    assert report["launchpad_project"] == "arkhe-core"


def test_multi_arch_custom_subset_alias_and_errors():
    multi = ArkheMultiArchBuilder(ArkheCoreImageBuilder())
    assert multi.get_multi_arch_report()["error"] == "Multi-arch build not configured"
    with pytest.raises(RuntimeError, match="not configured"):
        multi.build_for_architecture("arm64")

    multi.create_multi_arch_build(["x86_64"])
    image = multi.build_for_architecture("x86_64")
    assert image.model_assertion.architecture == "amd64"
    assert image.build_config.output_filename == "arkhe-core-26-amd64.img"
    with pytest.raises(RuntimeError, match="not in configured builds"):
        multi.build_for_architecture("arm64")
    with pytest.raises(RuntimeError, match="Unsupported architecture"):
        multi.create_multi_arch_build(["mips64"])


def test_full_integration_cicd_multi_arch_core_builder():
    builder = ArkheCoreImageBuilder()
    report = builder.build_for_architecture("arm64")
    assert report["constitutional_principles"]["P8"] is True

    cicd = ArkheCICDPipeline(builder)
    cicd.create_pipeline(trigger="tag", branch="main")
    for stage in cicd.pipeline.stages:
        cicd.execute_stage(stage.name, success=True)

    multi = ArkheMultiArchBuilder(builder)
    multi.create_multi_arch_build(["arm64", "amd64"])
    multi.build_for_architecture("arm64")
    multi.build_for_architecture("amd64")

    assert cicd.get_pipeline_report()["overall_status"] == "success"
    assert multi.get_multi_arch_report()["builds_completed"] == ["arm64", "amd64"]
    stages = [entry["stage"] for entry in builder._stage_log]
    assert BuildStage.CI_CD_PIPELINE.value in stages
    assert BuildStage.MULTI_ARCH_BUILD.value in stages
