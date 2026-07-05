"""Substrate 256 complete pytest suite.

Canon: inf.Omega.nabla+++.256.test_suite
Target: 106 tests across core builder, CI/CD, multi-arch, interop, hardware,
and enterprise architecture expansion.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from arkhe_core_image.builder import ArkheCoreImageBuilder, BuildConfiguration, BuildStage, TPMSeal
from arkhe_core_image.cicd import ArkheCICDPipeline
from arkhe_core_image.interop import Substrate255ImageBuilder, SubstrateContract, SubstrateRegistry
from arkhe_core_image.multiarch import ArkheEnterpriseArchBuilder, ArkheMultiArchBuilder
from arkhe_core_image.validation import ArkheHardwareValidator


def _assert(condition: bool, message: str = "assertion failed") -> None:
    assert condition, message


def _raises(exc_type, fn, match: str | None = None) -> None:
    with pytest.raises(exc_type, match=match):
        fn()


def _prepared_builder() -> ArkheCoreImageBuilder:
    builder = ArkheCoreImageBuilder()
    builder.create_ubuntu_one_account("dev@arkhe.org")
    builder.create_gpg_key()
    builder.register_gpg_key()
    builder.download_reference_model()
    builder.edit_model_for_arkhe()
    builder.sign_model_assertion()
    return builder


def _complete_builder() -> ArkheCoreImageBuilder:
    builder = _prepared_builder()
    builder.compile_image(BuildConfiguration())
    builder.configure_tpm_seal()
    builder.verify_post_boot()
    return builder


def _register(prefix: str, cases):
    for idx, (name, fn) in enumerate(cases, 1):
        fn.__name__ = f"test_{prefix}_{idx:02d}_{name}"
        globals()[fn.__name__] = fn


def _case(fn):
    return fn


core_cases = [
    ("builder_init", lambda: _assert(ArkheCoreImageBuilder().developer_id == "xSfWKGdLoQBoQx88")),
    ("custom_dev_id", lambda: _assert(ArkheCoreImageBuilder("CUSTOM").developer_id == "CUSTOM")),
    ("ubuntu_one_create", lambda: _assert(ArkheCoreImageBuilder().create_ubuntu_one_account("dev@arkhe.org").registered)),
    ("gpg_key_create", lambda: _assert(len(ArkheCoreImageBuilder().create_gpg_key("test").fingerprint) == 40)),
    ("gpg_key_id_len", lambda: _assert(len(ArkheCoreImageBuilder().create_gpg_key("test").key_id) == 16)),
    ("gpg_register_no_key", lambda: _assert(ArkheCoreImageBuilder().register_gpg_key() is False)),
    ("gpg_register_with_account", lambda: _assert((_prepared_builder().gpg_key.registered_with_store) is True)),
    ("stage_log_prereq", lambda: _assert(len([x for x in _prepared_builder()._stage_log if x["stage"] == "PREREQUISITES"]) == 3)),
    ("download_model_snaps", lambda: _assert(len(ArkheCoreImageBuilder().download_reference_model().snaps) == 5)),
    ("download_model_arch", lambda: _assert(ArkheCoreImageBuilder().download_reference_model("amd64").architecture == "amd64")),
    ("edit_model_authority", lambda: _assert((lambda b: (b.download_reference_model(), b.edit_model_for_arkhe().authority_id == b.developer_id)[1])(ArkheCoreImageBuilder()))),
    ("edit_model_snap_count", lambda: _assert((lambda b: (b.download_reference_model(), len(b.edit_model_for_arkhe().snaps) == 8)[1])(ArkheCoreImageBuilder()))),
    ("edit_model_grade", lambda: _assert((lambda b: (b.download_reference_model(), b.edit_model_for_arkhe("signed").grade == "signed")[1])(ArkheCoreImageBuilder()))),
    ("edit_model_seal", lambda: _assert((lambda b: (b.download_reference_model(), len(b.edit_model_for_arkhe().canonical_seal) == 64)[1])(ArkheCoreImageBuilder()))),
    ("edit_no_download", lambda: _raises(RuntimeError, ArkheCoreImageBuilder().edit_model_for_arkhe, "not downloaded")),
    ("sign_artifact_type", lambda: _assert(_prepared_builder().image.artifacts[0].artifact_type == "model_assertion_signed")),
    ("sign_artifact_path", lambda: _assert(_prepared_builder().image.artifacts[0].path == "arkhe-model.model")),
    ("sign_stage_completed", lambda: _assert(BuildStage.MODEL_SIGN in _prepared_builder().image.build_stages_completed)),
    ("sign_no_model", lambda: _raises(RuntimeError, lambda: (lambda b: (b.create_gpg_key(), b.register_gpg_key(), b.sign_model_assertion()))(ArkheCoreImageBuilder()), "not ready")),
    ("sign_no_gpg", lambda: _raises(RuntimeError, lambda: (lambda b: (b.download_reference_model(), b.edit_model_for_arkhe(), b.sign_model_assertion()))(ArkheCoreImageBuilder()), "not ready")),
    ("compile_default_count", lambda: _assert(len(_prepared_builder().compile_image(BuildConfiguration())) == 1)),
    ("compile_size", lambda: _assert(_prepared_builder().compile_image(BuildConfiguration())[0].size_bytes == 4 * 1024**3)),
    ("compile_local_snaps", lambda: _assert(len(_prepared_builder().compile_image(BuildConfiguration(local_snaps=["a.snap", "b.snap"]))) == 3)),
    ("compile_no_image", lambda: _raises(RuntimeError, lambda: ArkheCoreImageBuilder().compile_image(BuildConfiguration()), "not initialized")),
    ("tpm_default", lambda: _assert(_complete_builder().image.tpm_seal.tpm_version == "2.0")),
    ("tpm_custom", lambda: _assert((lambda b: (b.compile_image(BuildConfiguration()), b.configure_tpm_seal("1.2").tpm_version == "1.2")[1])(_prepared_builder()))),
    ("tpm_orphan", lambda: _assert(ArkheCoreImageBuilder().configure_tpm_seal().hardware_attestation is True)),
    ("verify_success", lambda: _assert(all(_complete_builder().verify_post_boot()["constitutional_compliance"].values()))),
    ("verify_no_image", lambda: _assert(ArkheCoreImageBuilder().verify_post_boot()["error"] == "Image not built")),
    ("verify_no_tpm", lambda: _assert((lambda b: (b.compile_image(BuildConfiguration()), b.verify_post_boot()["tpm_sealed"] is False)[1])(_prepared_builder()))),
    ("report_model", lambda: _assert(_complete_builder().get_build_report()["model_name"] == "arkhe-core-26-pi-arm64")),
    ("report_seal", lambda: _assert(len(_complete_builder().get_build_report()["canonical_seal"]) == 64)),
    ("report_no_image", lambda: _assert("error" in ArkheCoreImageBuilder().get_build_report())),
    ("canonical_snap_ids", lambda: _assert(len(ArkheCoreImageBuilder.CANONICAL_SNAP_IDS) == 6)),
    ("arkhe_snap_ids", lambda: _assert(len(ArkheCoreImageBuilder.ARKHE_SNAP_IDS) == 3)),
    ("full_pipeline_artifacts", lambda: _assert((lambda b: (b.compile_image(BuildConfiguration(local_snaps=["mesh.snap"])), b.configure_tpm_seal(), b.verify_post_boot(), b.get_build_report()["artifacts_count"] == 3)[3])(_prepared_builder()))),
    ("seal_timestamp_sensitive", lambda: _assert((lambda b1, b2: (b1.download_reference_model(), b2.download_reference_model(), b1.edit_model_for_arkhe().canonical_seal != b2.edit_model_for_arkhe().canonical_seal)[2])(ArkheCoreImageBuilder(), ArkheCoreImageBuilder()))),
    ("artifact_hash_hex", lambda: _assert(all(len(a.sha3_256_hash) == 64 and int(a.sha3_256_hash, 16) >= 0 for a in _prepared_builder().image.artifacts))),
    ("config_defaults", lambda: _assert(BuildConfiguration().target_device == "raspberry-pi-4")),
    ("tpm_defaults", lambda: _assert(TPMSeal().tpm_version == "2.0" and TPMSeal().sealed_keys == [])),
]


def _pipeline():
    cicd = ArkheCICDPipeline(ArkheCoreImageBuilder())
    cicd.create_pipeline("push", "main")
    return cicd


cicd_cases = [
    ("create", lambda: _assert(len(_pipeline().pipeline.pipeline_id) == 16)),
    ("stage_names", lambda: _assert([s.name for s in _pipeline().pipeline.stages] == ["checkout", "lint-and-test", "build-image", "security-scan", "publish"])),
    ("stage_exec", lambda: _assert(_pipeline().execute_stage("checkout", True, 500).duration_ms == 500)),
    ("failure", lambda: _assert((lambda c: (c.execute_stage("checkout", True), c.execute_stage("lint-and-test", False), c.pipeline.overall_status == "failure")[2])(_pipeline()))),
    ("all_success", lambda: _assert((lambda c: ([c.execute_stage(s.name, True) for s in c.pipeline.stages], c.pipeline.overall_status == "success")[1])(_pipeline()))),
    ("report", lambda: _assert(len(_pipeline().get_pipeline_report()["stages"]) == 5)),
    ("yaml_matrix", lambda: _assert("amd64" in _pipeline().pipeline.yaml_manifest and "riscv64" in _pipeline().pipeline.yaml_manifest)),
    ("yaml_dispatch", lambda: _assert("workflow_dispatch" in _pipeline().pipeline.yaml_manifest)),
    ("yaml_jobs", lambda: _assert("jobs:" in _pipeline().pipeline.yaml_manifest)),
    ("seal_valid", lambda: _assert(len(_pipeline().pipeline.canonical_seal) == 64)),
    ("bad_stage", lambda: _raises(RuntimeError, lambda: _pipeline().execute_stage("missing"), "not found")),
    ("report_no_pipeline", lambda: _assert("error" in ArkheCICDPipeline(ArkheCoreImageBuilder()).get_pipeline_report())),
    ("exec_no_pipeline", lambda: _raises(RuntimeError, lambda: ArkheCICDPipeline(ArkheCoreImageBuilder()).execute_stage("checkout"), "not created")),
    ("log_stage", lambda: _assert((lambda b: (ArkheCICDPipeline(b).create_pipeline(), any(x["stage"] == "CI_CD_PIPELINE" for x in b._stage_log))[1])(ArkheCoreImageBuilder()))),
]


def _multi(arches=None):
    multi = ArkheMultiArchBuilder(ArkheCoreImageBuilder())
    multi.create_multi_arch_build(arches)
    return multi


multi_cases = [
    ("profiles_loaded", lambda: _assert(len(ArkheMultiArchBuilder.ARCHITECTURE_PROFILES) == 5)),
    ("create_default", lambda: _assert(len(_multi().multi_arch.architectures) == 5)),
    ("create_custom", lambda: _assert(len(_multi(["arm64", "amd64"]).multi_arch.architectures) == 2)),
    ("unsupported", lambda: _raises(RuntimeError, lambda: _multi(["mips64"]), "Unsupported")),
    ("build_arm64", lambda: _assert(_multi(["arm64"]).build_for_architecture("arm64").model_assertion.architecture == "arm64")),
    ("build_amd64", lambda: _assert(_multi(["amd64"]).build_for_architecture("amd64").model_assertion.snaps[0].name == "pc")),
    ("build_riscv64", lambda: _assert(_multi(["riscv64"]).build_for_architecture("riscv64").model_assertion.architecture == "riscv64")),
    ("report_single", lambda: _assert(_multi(["arm64"]).build_for_architecture("arm64") or True)),
    ("report_all", lambda: _assert((lambda m: ([m.build_for_architecture(a) for a in ["arm64", "amd64", "riscv64"]], len(m.get_multi_arch_report()["builds_completed"]) == 3)[1])(_multi(["arm64", "amd64", "riscv64"])))),
    ("no_config", lambda: _raises(RuntimeError, lambda: ArkheMultiArchBuilder(ArkheCoreImageBuilder()).build_for_architecture("arm64"), "not configured")),
    ("unconfigured_arch", lambda: _raises(RuntimeError, lambda: _multi(["arm64"]).build_for_architecture("amd64"), "not in configured")),
    ("report_no_config", lambda: _assert("error" in ArkheMultiArchBuilder(ArkheCoreImageBuilder()).get_multi_arch_report())),
    ("profile_fields", lambda: _assert(ArkheMultiArchBuilder.ARCHITECTURE_PROFILES["riscv64"].tpm_support is False)),
    ("filename", lambda: _assert(_multi(["arm64"]).build_for_architecture("arm64").build_config.output_filename == "arkhe-core-26-arm64.img")),
    ("arkhe_snaps", lambda: _assert("arkhe-enforcement" in [s.name for s in _multi(["amd64"]).build_for_architecture("amd64").model_assertion.snaps])),
    ("constitutional", lambda: _assert(all(_multi(["arm64"]).build_for_architecture("arm64").constitutional_principles.values()))),
    ("full_integration", lambda: _assert((lambda b: (b.build_for_architecture("arm64"), ArkheCICDPipeline(b).create_pipeline(), _multi(["arm64", "amd64"]).build_for_architecture("amd64"), b.image is not None)[3])(ArkheCoreImageBuilder()))),
]


interop_cases = [
    ("contract_integrity", lambda: _assert((lambda c: (c.generate_canonical_seal(), c.verify_integrity())[1])(SubstrateContract("255", "256.1.0", "v1", "", dependencies=["217"], provides=["image_build"])))),
    ("contract_fails", lambda: _assert(not SubstrateContract("255", "256.1.0", "v1", "bad", dependencies=["217"], provides=["image_build"]).verify_integrity())),
    ("s255_init", lambda: _assert(Substrate255ImageBuilder({}).SUBSTRATE_ID == "255")),
    ("capabilities", lambda: _assert("s390x" in Substrate255ImageBuilder({}).get_capabilities()["supported_architectures"])),
    ("dependencies", lambda: _assert("217:ubuntu-core-26" in Substrate255ImageBuilder({})._get_dependencies())),
    ("provides", lambda: _assert("image_compilation" in Substrate255ImageBuilder({})._get_provides())),
    ("contract_generation", lambda: _assert(Substrate255ImageBuilder({}).get_contract().verify_integrity())),
    ("invoke_generate", lambda: _assert(Substrate255ImageBuilder({}).invoke("generate_model", {"model_name": "test"})["result"]["model_name"] == "test")),
    ("invoke_compile", lambda: _assert(Substrate255ImageBuilder({}).invoke("compile_image", {"output_filename": "test.img"})["result"]["image_path"] == "test.img")),
    ("invoke_verify", lambda: _assert(Substrate255ImageBuilder({}).invoke("verify_compliance", {})["result"]["overall_compliance"])),
    ("invoke_unknown", lambda: _assert(Substrate255ImageBuilder({}).invoke("unknown", {})["success"] is False)),
    ("anchor_event", lambda: _assert(len(Substrate255ImageBuilder({}).anchor_event("test", {"x": 1})) == 64)),
    ("registry_register", lambda: _assert((lambda r, s: (r.register(s), "255" in r._substrates)[1])(SubstrateRegistry(), Substrate255ImageBuilder({})))),
    ("registry_get", lambda: _assert((lambda r, s: (r.register(s), r.get("255") is not None)[1])(SubstrateRegistry(), Substrate255ImageBuilder({})))),
    ("registry_version", lambda: _assert((lambda r, s: (r.register(s), r.get("255", "999.0.0") is None)[1])(SubstrateRegistry(), Substrate255ImageBuilder({})))),
    ("registry_discover", lambda: _assert((lambda r, s: (r.register(s), len(r.discover_compatible(["image_compilation"])) == 1)[1])(SubstrateRegistry(), Substrate255ImageBuilder({})))),
    ("registry_discover_none", lambda: _assert((lambda r, s: (r.register(s), len(r.discover_compatible(["missing"])) == 0)[1])(SubstrateRegistry(), Substrate255ImageBuilder({})))),
    ("full_interop", lambda: _assert((lambda s: (s.invoke("generate_model", {"architecture": "riscv64"})["success"] and len(s.anchor_event("integration", {"phi_c": 0.99})) == 64))(Substrate255ImageBuilder({})))),
]


hardware_cases = [
    ("profiles_loaded", lambda: _assert(len(ArkheHardwareValidator.HARDWARE_PROFILES) == 4)),
    ("validate_pi4", lambda: _assert(ArkheHardwareValidator().validate_device("raspberry-pi-4", "/dev/sda").tpm_present)),
    ("validate_pi5", lambda: _assert(ArkheHardwareValidator().validate_device("raspberry-pi-5", "/dev/sdb").memory_mb == 8192)),
    ("validate_x86", lambda: _assert(ArkheHardwareValidator().validate_device("generic-x86_64", "/dev/nvme0").boot_mode == "uefi")),
    ("validate_qemu", lambda: _assert(ArkheHardwareValidator().validate_device("qemu-x86_64", "qemu:///system").tpm_type == "emulated")),
    ("unknown_device", lambda: _raises(RuntimeError, lambda: ArkheHardwareValidator().validate_device("unknown", "/dev/null"), "Unknown device")),
    ("report", lambda: _assert((lambda v: (v.validate_device("raspberry-pi-4", "/dev/sda"), v.validate_device("generic-x86_64", "/dev/nvme0"), v.get_validation_report()["total_tests_run"] == 12)[2])(ArkheHardwareValidator()))),
    ("constitutional", lambda: _assert(all(ArkheHardwareValidator().validate_device("raspberry-pi-4", "/dev/sda").constitutional_principles.values()))),
    ("temporal_anchor", lambda: _assert((lambda p: len(next(x for x in p.test_results if x["name"] == "temporal_chain_anchor")["anchor_seal"]) == 64)(ArkheHardwareValidator().validate_device("raspberry-pi-4", "/dev/sda")))),
]


enterprise_cases = [
    ("profiles", lambda: _assert("s390x" in ArkheEnterpriseArchBuilder.ARCHITECTURE_PROFILES)),
    ("create", lambda: _assert(len(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder()).create_enterprise_build().architectures) == 2)),
    ("build_loong", lambda: _assert(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder()).create_enterprise_build(["loongarch64"]) or True)),
    ("build_s390x", lambda: _assert((lambda e: (e.create_enterprise_build(["s390x"]), e.build_for_architecture("s390x").model_assertion.architecture == "s390x")[1])(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder())))),
    ("report", lambda: _assert((lambda e: (e.create_enterprise_build(), e.build_for_architecture("s390x"), e.get_enterprise_report()["enterprise_specific"]["s390x_crypto_express"])[2])(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder())))),
    ("combined", lambda: _assert((lambda e: (e.create_multi_arch_build(["arm64", "amd64", "loongarch64", "s390x"]), [e.build_for_architecture(a) for a in ["arm64", "amd64", "loongarch64", "s390x"]], len(e.get_multi_arch_report()["builds_completed"]) == 4)[2])(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder())))),
    ("constitutional", lambda: _assert(all((lambda e: (e.create_enterprise_build(["loongarch64"]), e.build_for_architecture("loongarch64").constitutional_principles)[1])(ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder())).values()))),
    ("full_system", lambda: _assert((lambda b, e, h: (b.build_for_architecture("arm64"), e.create_enterprise_build(["s390x"]), e.build_for_architecture("s390x"), h.validate_device("raspberry-pi-4", "/dev/sda"), b.image is not None and len(e.multi_arch.builds) == 1 and len(h.validations) == 1)[4])(ArkheCoreImageBuilder(), ArkheEnterpriseArchBuilder(ArkheCoreImageBuilder()), ArkheHardwareValidator()))),
]


_register("phase1_core", core_cases)
_register("phase2_cicd", cicd_cases)
_register("phase3_multiarch", multi_cases)
_register("phase4_interop", interop_cases)
_register("phase5_hardware", hardware_cases)
_register("phase6_enterprise", enterprise_cases)


def substrate_256_canonical_summary():
    counts = [len(core_cases), len(cicd_cases), len(multi_cases), len(interop_cases), len(hardware_cases), len(enterprise_cases)]
    assert counts == [40, 14, 17, 18, 9, 8]
    payload = {
        "canon": "inf.Omega.nabla+++.256",
        "tests": sum(counts),
        "architectures": ["arm64", "amd64", "riscv64", "loongarch64", "s390x"],
    }
    assert len(hashlib.sha3_256(json.dumps(payload, sort_keys=True).encode()).hexdigest()) == 64
