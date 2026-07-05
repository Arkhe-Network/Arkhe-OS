from pathlib import Path

from substrate_256 import HardwareDevice, HardwareValidationLab, Substrate255ImageBuilder, SubstrateRegistry
from substrate_266 import ArkheMultiArchBuilder, SUPPORTED_TARGETS, build_all_arch


ROOT = Path(__file__).resolve().parents[1]


def test_hardware_validation_plan_defaults_and_results():
    lab = HardwareValidationLab()
    plan = lab.generate_validation_plan()
    assert plan["substrate"] == 256
    assert len(plan["required_devices"]) == 3
    assert len(plan["canonical_seal"]) == 64

    compliance = {"P1": True, "P3": True, "P6": True, "P7": True, "P8": True}
    result = lab.record_result("rpi5-lab-01", "arkhe-core-26-arm64.img", True, True, True, compliance, duration_ms=45000)
    assert result.boot_verified is True
    assert len(result.canonical_seal) == 64

    report = lab.get_lab_report()
    assert report["devices_registered"] == 3
    assert report["results_passed"] == 1
    assert "rpi4-lab-01" in report["pending_devices"]


def test_hardware_validation_registers_enterprise_devices():
    lab = HardwareValidationLab(devices=[])
    lab.register_device(HardwareDevice("loong-lab-01", "generic-loongarch64", "loongarch64", "none", False))
    lab.register_device(HardwareDevice("z-lab-01", "ibm-z-mainframe", "s390x", "2.0", True, secure_boot=True))
    plan = lab.generate_validation_plan()
    architectures = {device["architecture"] for device in plan["required_devices"]}
    assert architectures == {"loongarch64", "s390x"}


def test_substrate_interop_registry_and_invocations():
    substrate = Substrate255ImageBuilder({"temporal_anchor": "temporal://substrate-256-test"})
    registry = SubstrateRegistry()
    assert registry.register(substrate) is True
    assert registry.get("255") is substrate

    compatible = registry.discover_compatible(["image_compilation", "constitutional_verification"])
    assert compatible == [substrate]
    contract = substrate.get_contract()
    assert contract.verify_integrity() is True
    assert "temporal_anchoring" in contract.provides

    capabilities = substrate.get_capabilities()
    assert "loongarch64" in capabilities["supported_architectures"]
    assert "s390x" in capabilities["supported_architectures"]

    generated = substrate.invoke("generate_model", {"architecture": "s390x", "grade": "signed"})
    assert generated["success"] is True
    assert generated["result"]["architecture"] == "s390x"
    compiled = substrate.invoke("compile_image", {"architecture": "loongarch64"})
    assert compiled["success"] is True
    assert compiled["result"]["constitutional_compliance"]["P8"] is True
    assert "available" in substrate.invoke("missing_method", {})


def test_enterprise_architectures_in_multi_arch_and_manifest(tmp_path):
    assert "loongarch64" in SUPPORTED_TARGETS
    assert "s390x" in SUPPORTED_TARGETS

    manifest = build_all_arch(["loongarch64", "s390x"], tmp_path)
    assert manifest["targets"] == ["loongarch64", "s390x"]
    assert manifest["reports"]["loongarch64"]["architecture_profile"]["target_device"] == "generic-loongarch64"
    assert manifest["reports"]["s390x"]["architecture_profile"]["target_device"] == "ibm-z-mainframe"

    multi = ArkheMultiArchBuilder.__new__(ArkheMultiArchBuilder)
    assert "loongarch64" in multi.ARCHITECTURE_PROFILES
    assert "s390x" in multi.ARCHITECTURE_PROFILES


def test_platform_config_and_workflow_cover_enterprise_architectures():
    config = ROOT / "substrate_256" / "platform_config.yaml"
    workflow = ROOT / ".github" / "workflows" / "arkhe-core-build.yml"
    assert config.exists()
    assert workflow.exists()
    config_text = config.read_text(encoding="utf-8")
    workflow_text = workflow.read_text(encoding="utf-8")
    for token in ["loongarch64", "s390x", "core26"]:
        assert token in config_text
        assert token in workflow_text
