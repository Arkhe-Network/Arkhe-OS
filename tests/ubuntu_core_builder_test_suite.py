from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from substrate_255 import (
    ArkheCoreImageBuilder,
    BuildArtifact,
    BuildConfiguration,
    BuildStage,
    ModelAssertion,
    TPMSeal,
)

import hashlib
import json
import time
from typing import List


TESTS_PASSED = 0
TESTS_FAILED = 0
TEST_RESULTS: List[tuple] = []


def test(name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global TESTS_PASSED, TESTS_FAILED, TEST_RESULTS
            try:
                func(*args, **kwargs)
                TESTS_PASSED += 1
                TEST_RESULTS.append((name, "PASS", None))
                print(f"  PASS {name}")
            except Exception as e:
                TESTS_FAILED += 1
                TEST_RESULTS.append((name, "FAIL", str(e)))
                print(f"  FAIL {name}: {e}")
        wrapper.__name__ = func.__name__
        wrapper()
        return wrapper
    return decorator


def prepared_builder() -> ArkheCoreImageBuilder:
    builder = ArkheCoreImageBuilder()
    builder.create_ubuntu_one_account("dev@arkhe.org")
    builder.create_gpg_key()
    builder.register_gpg_key()
    builder.download_reference_model()
    builder.edit_model_for_arkhe()
    builder.sign_model_assertion()
    return builder


@test("T01: Builder initializes with default developer_id")
def t01_builder_init():
    builder = ArkheCoreImageBuilder()
    assert builder.developer_id == "xSfWKGdLoQBoQx88"
    assert builder.ubuntu_one is None
    assert builder.gpg_key is None
    assert builder.model_assertion is None
    assert builder.image is None
    assert len(builder._stage_log) == 0


@test("T02: Custom developer_id override")
def t02_custom_dev_id():
    builder = ArkheCoreImageBuilder(developer_id="CUSTOM_ID_123")
    assert builder.developer_id == "CUSTOM_ID_123"


@test("T03: Ubuntu One account creation")
def t03_ubuntu_one_create():
    builder = ArkheCoreImageBuilder()
    account = builder.create_ubuntu_one_account("dev@arkhe.org")
    assert account.developer_id == builder.developer_id
    assert account.email == "dev@arkhe.org"
    assert account.registered is True
    assert account.gpg_key_id is None
    assert builder.ubuntu_one is account
    assert len(builder._stage_log) == 1
    assert builder._stage_log[0]["stage"] == "PREREQUISITES"


@test("T04: GPG key creation generates valid fingerprint")
def t04_gpg_key_create():
    builder = ArkheCoreImageBuilder()
    key = builder.create_gpg_key("test-key")
    assert key.key_name == "test-key"
    assert len(key.fingerprint) == 40
    assert len(key.key_id) == 16
    assert key.created > 0
    assert key.registered_with_store is False
    assert builder.gpg_key is key


@test("T05: GPG key registration links to Ubuntu One account")
def t05_gpg_register():
    builder = ArkheCoreImageBuilder()
    builder.create_ubuntu_one_account("dev@arkhe.org")
    builder.create_gpg_key()
    result = builder.register_gpg_key()
    assert result is True
    assert builder.gpg_key.registered_with_store is True
    assert builder.ubuntu_one.gpg_key_id == builder.gpg_key.key_id


@test("T06: GPG registration fails without key")
def t06_gpg_register_no_key():
    builder = ArkheCoreImageBuilder()
    assert builder.register_gpg_key() is False


@test("T07: Multiple stage logs accumulate correctly")
def t07_stage_log_accumulation():
    builder = ArkheCoreImageBuilder()
    builder.create_ubuntu_one_account("a@arkhe.org")
    builder.create_gpg_key()
    builder.register_gpg_key()
    assert len(builder._stage_log) == 3
    assert [log["stage"] for log in builder._stage_log] == ["PREREQUISITES"] * 3


@test("T08: Reference model download creates correct base snaps")
def t08_download_model():
    builder = ArkheCoreImageBuilder()
    model = builder.download_reference_model()
    assert model.assertion_type == "model"
    assert model.series == "16"
    assert model.architecture == "arm64"
    assert model.authority_id == "canonical"
    assert model.brand_id == "canonical"
    assert len(model.snaps) == 5
    snap_names = [s.name for s in model.snaps]
    assert {"pi", "pi-kernel", "core26", "snapd", "console-conf"}.issubset(snap_names)
    assert builder.model_assertion is model
    assert builder._stage_log[0]["stage"] == "MODEL_DOWNLOAD"


@test("T09: Model edit transforms authority and injects Arkhe snaps")
def t09_edit_model():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    model = builder.edit_model_for_arkhe()
    assert model.authority_id == builder.developer_id
    assert model.brand_id == builder.developer_id
    assert model.model_name == "arkhe-core-26-pi-arm64"
    assert model.base == "core26"
    assert model.grade == "dangerous"
    assert len(model.snaps) == 8
    arkhe_names = [s.name for s in model.snaps if s.name.startswith("arkhe") or s.name in ["temporal-anchor", "pqc-revocation"]]
    assert len(arkhe_names) == 3
    assert len(model.canonical_seal) == 64
    assert builder._stage_log[-1]["stage"] == "MODEL_EDIT"


@test("T10: Model edit with custom grade")
def t10_edit_model_grade():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    assert builder.edit_model_for_arkhe(grade="signed").grade == "signed"


@test("T11: Model edit fails without prior download")
def t11_edit_no_download():
    builder = ArkheCoreImageBuilder()
    try:
        builder.edit_model_for_arkhe()
        assert False
    except RuntimeError as e:
        assert "not downloaded" in str(e)


@test("T12: Model assertion signing requires GPG registration")
def t12_sign_requires_gpg():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    builder.edit_model_for_arkhe()
    try:
        builder.sign_model_assertion()
        assert False
    except RuntimeError as e:
        assert "not registered" in str(e)


@test("T13: Model assertion signing produces valid artifact")
def t13_sign_model():
    builder = prepared_builder()
    artifact = builder.image.artifacts[0]
    assert artifact.artifact_type == "model_assertion_signed"
    assert artifact.path == "arkhe-model.model"
    assert artifact.size_bytes > 0
    assert len(artifact.sha3_256_hash) == 64
    assert len(artifact.canonical_seal) == 64
    assert BuildStage.MODEL_SIGN in builder.image.build_stages_completed
    assert builder._stage_log[-1]["stage"] == "MODEL_SIGN"


@test("T14: Sign fails without model assertion")
def t14_sign_no_model():
    builder = ArkheCoreImageBuilder()
    builder.create_gpg_key()
    builder.register_gpg_key()
    try:
        builder.sign_model_assertion()
        assert False
    except RuntimeError as e:
        assert "not ready" in str(e)


@test("T15: Sign fails without GPG key")
def t15_sign_no_gpg():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    builder.edit_model_for_arkhe()
    try:
        builder.sign_model_assertion()
        assert False
    except RuntimeError as e:
        assert "not ready" in str(e)


@test("T16: Image compilation with default config")
def t16_compile_default():
    builder = prepared_builder()
    artifacts = builder.compile_image(BuildConfiguration())
    img = artifacts[0]
    assert len(artifacts) == 1
    assert img.artifact_type == "bootable_image"
    assert img.size_bytes == 4 * 1024 * 1024 * 1024
    assert img.path == "pi.img"
    assert len(img.sha3_256_hash) == 64
    assert len(img.canonical_seal) == 64
    assert BuildStage.IMAGE_COMPILE in builder.image.build_stages_completed


@test("T17: Image compilation with local snaps")
def t17_compile_with_snaps():
    builder = prepared_builder()
    config = BuildConfiguration(local_snaps=["/path/to/snap1.snap", "/path/to/snap2.snap"], output_filename="custom.img")
    artifacts = builder.compile_image(config)
    assert len(artifacts) == 3
    assert artifacts[0].path == "custom.img"
    assert artifacts[1].artifact_type == "local_snap"
    assert artifacts[2].artifact_type == "local_snap"
    assert len(builder.image.artifacts) == 4


@test("T18: Compile fails without initialized image")
def t18_compile_no_image():
    try:
        ArkheCoreImageBuilder().compile_image(BuildConfiguration())
        assert False
    except RuntimeError as e:
        assert "not initialized" in str(e)


@test("T19: TPM seal configuration with defaults")
def t19_tpm_seal_default():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    seal = builder.configure_tpm_seal()
    assert seal.tpm_version == "2.0"
    assert len(seal.sealed_keys) == 3
    assert all(len(k) == 32 for k in seal.sealed_keys)
    assert seal.op_tee_enabled is True
    assert seal.hardware_attestation is True
    assert builder.image.tpm_seal is seal
    assert builder._stage_log[-1]["stage"] == "VERIFICATION"


@test("T20: TPM seal with custom version")
def t20_tpm_seal_custom():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    assert builder.configure_tpm_seal(tpm_version="1.2").tpm_version == "1.2"


@test("T21: TPM seal works without image")
def t21_tpm_orphan():
    builder = ArkheCoreImageBuilder()
    seal = builder.configure_tpm_seal()
    assert seal is not None
    assert builder.image is None


@test("T22: Post-boot verification succeeds with all snaps")
def t22_verify_success():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    builder.configure_tpm_seal()
    result = builder.verify_post_boot()
    assert result["model_assertion_valid"] is True
    assert result["snaps_installed"] == 3
    assert result["expected_snaps"] == 3
    assert result["tpm_sealed"] is True
    assert all(result["constitutional_compliance"][p] is True for p in ["P1", "P3", "P6", "P7", "P8"])
    assert builder.image.constitutional_principles == result["constitutional_compliance"]
    assert BuildStage.VERIFICATION in builder.image.build_stages_completed


@test("T23: Post-boot verification fails without image")
def t23_verify_no_image():
    assert ArkheCoreImageBuilder().verify_post_boot()["error"] == "Image not built"


@test("T24: Post-boot with missing TPM seal")
def t24_verify_no_tpm():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    result = builder.verify_post_boot()
    assert result["tpm_sealed"] is False
    assert result["snaps_installed"] == 3


@test("T25: Build report contains all expected fields")
def t25_build_report():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    builder.configure_tpm_seal()
    builder.verify_post_boot()
    report = builder.get_build_report()
    assert report["model_name"] == "arkhe-core-26-pi-arm64"
    assert report["base"] == "core26"
    assert report["grade"] == "dangerous"
    assert report["architecture"] == "arm64"
    assert report["tpm_sealed"] is True
    assert len(report["stages_completed"]) == 5
    assert report["artifacts_count"] == 2
    assert len(report["canonical_seal"]) == 64
    assert report["constitutional_principles"]["P1"] is True
    assert report["uc26"]["release_date"] == "2026-05-14"
    assert report["uc26"]["base_composition"] == "chisel"
    assert report["uc26"]["python_runtime_available"] is False


@test("T26: Build report fails without image")
def t26_report_no_image():
    assert ArkheCoreImageBuilder().get_build_report()["error"] == "No image built"


@test("T27: Canonical snap IDs are all present")
def t27_canonical_snap_ids():
    ids = ArkheCoreImageBuilder.CANONICAL_SNAP_IDS
    assert len(ids) == 6
    assert all(len(v) > 0 for v in ids.values())
    assert "pi" in ids and "pi-kernel" in ids and "core26" in ids


@test("T28: Arkhe snap IDs are all present")
def t28_arkhe_snap_ids():
    ids = ArkheCoreImageBuilder.ARKHE_SNAP_IDS
    assert len(ids) == 3
    assert {"arkhe-enforcement", "temporal-anchor", "pqc-revocation"}.issubset(ids)


@test("T29: Full end-to-end build pipeline")
def t29_full_pipeline():
    builder = ArkheCoreImageBuilder()
    builder.create_ubuntu_one_account("pipeline@arkhe.org")
    builder.create_gpg_key("pipeline-key")
    builder.register_gpg_key()
    builder.download_reference_model()
    builder.edit_model_for_arkhe(grade="dangerous")
    builder.sign_model_assertion()
    builder.compile_image(BuildConfiguration(target_device="raspberry-pi-5", output_filename="arkhe-pi5.img", local_snaps=["/opt/snaps/arkhe-mesh.snap"]))
    builder.configure_tpm_seal()
    result = builder.verify_post_boot()
    report = builder.get_build_report()
    assert report["model_name"] == "arkhe-core-26-pi-arm64"
    assert report["artifacts_count"] == 3
    assert result["snaps_installed"] == 3
    assert result["tpm_sealed"] is True
    assert len(builder._stage_log) >= 8
    stages = [log["stage"] for log in builder._stage_log]
    for stage in ["PREREQUISITES", "MODEL_DOWNLOAD", "MODEL_EDIT", "MODEL_SIGN", "IMAGE_COMPILE", "VERIFICATION"]:
        assert stage in stages


@test("T30: Canonical seal is timestamp-sensitive and valid")
def t30_seal_determinism():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    seal1 = builder.edit_model_for_arkhe().canonical_seal
    builder2 = ArkheCoreImageBuilder()
    builder2.download_reference_model()
    seal2 = builder2.edit_model_for_arkhe().canonical_seal
    assert seal1 != seal2
    assert len(seal1) == 64 and len(seal2) == 64


@test("T31: Constitutional principles all True after verification")
def t31_constitutional_all_true():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    builder.configure_tpm_seal()
    builder.verify_post_boot()
    principles = builder.image.constitutional_principles
    assert len(principles) == 5
    assert all(v is True for v in principles.values())
    assert set(principles.keys()) == {"P1", "P3", "P6", "P7", "P8"}


@test("T32: Build artifact SHA3-256 hashes are valid hex")
def t32_artifact_hashes():
    builder = prepared_builder()
    builder.compile_image(BuildConfiguration())
    for artifact in builder.image.artifacts:
        assert len(artifact.sha3_256_hash) == 64
        int(artifact.sha3_256_hash, 16)
        assert len(artifact.canonical_seal) == 64
        int(artifact.canonical_seal, 16)


@test("T33: Timestamp ordering in stage log")
def t33_timestamp_ordering():
    builder = prepared_builder()
    timestamps = [log["timestamp"] for log in builder._stage_log]
    assert all(timestamps[i] <= timestamps[i + 1] for i in range(len(timestamps) - 1))


@test("T34: Model assertion snap types are valid")
def t34_snap_types():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    builder.edit_model_for_arkhe()
    valid_types = {"gadget", "kernel", "base", "snapd", "app"}
    assert all(snap.snap_type in valid_types for snap in builder.model_assertion.snaps)


@test("T35: Presence field defaults and overrides")
def t35_presence_field():
    builder = ArkheCoreImageBuilder()
    builder.download_reference_model()
    snaps = builder.model_assertion.snaps
    assert next(s for s in snaps if s.name == "console-conf").presence == "optional"
    assert next(s for s in snaps if s.name == "pi").presence == "required"


@test("T36: BuildConfiguration defaults")
def t36_config_defaults():
    config = BuildConfiguration()
    assert config.target_device == "raspberry-pi-4"
    assert config.image_format == "img"
    assert config.allow_kernel_mismatch is True
    assert config.validation_mode == "ignore"
    assert config.local_snaps == []
    assert config.output_filename == "pi.img"


@test("T37: BuildConfiguration custom values")
def t37_config_custom():
    config = BuildConfiguration(target_device="raspberry-pi-5", image_format="iso", allow_kernel_mismatch=False, validation_mode="strict", local_snaps=["a.snap", "b.snap"], output_filename="custom.img")
    assert config.target_device == "raspberry-pi-5"
    assert config.image_format == "iso"
    assert config.allow_kernel_mismatch is False
    assert config.validation_mode == "strict"
    assert config.local_snaps == ["a.snap", "b.snap"]
    assert config.output_filename == "custom.img"


@test("T38: ModelAssertion default values")
def t38_model_defaults():
    model = ModelAssertion()
    assert model.assertion_type == "model"
    assert model.series == "16"
    assert model.model_name == "arkhe-core-26-pi-arm64"
    assert model.architecture == "arm64"
    assert model.base == "core26"
    assert model.grade == "dangerous"
    assert model.snaps == []
    assert model.canonical_seal == ""
    assert model.uc26_release_date == "2026-05-14"


@test("T39: TPMSeal defaults")
def t39_tpm_defaults():
    seal = TPMSeal()
    assert seal.tpm_version == "2.0"
    assert seal.sealed_keys == []
    assert seal.op_tee_enabled is True
    assert seal.hardware_attestation is False


@test("T40: BuildArtifact fields")
def t40_artifact_fields():
    artifact = BuildArtifact("test", "/tmp/test", 1024, "a" * 64, "b" * 64, 1234567890)
    assert artifact.artifact_type == "test"
    assert artifact.path == "/tmp/test"
    assert artifact.size_bytes == 1024
    assert artifact.sha3_256_hash == "a" * 64
    assert artifact.canonical_seal == "b" * 64
    assert artifact.timestamp == 1234567890


def main() -> bool:
    print()
    print("=" * 70)
    print("ARKHE OS SUBSTRATE 255 - Ubuntu Core 26 Image Builder")
    print("=" * 70)
    total = TESTS_PASSED + TESTS_FAILED
    print(f"  Total tests: {total}")
    print(f"  Passed: {TESTS_PASSED}")
    print(f"  Failed: {TESTS_FAILED}")
    print(f"  Pass rate: {TESTS_PASSED / total * 100:.1f}%")
    if TESTS_FAILED:
        print()
        print("Failed tests:")
        for name, status, error in TEST_RESULTS:
            if status != "PASS":
                print(f"  - {name}: {error}")
    seal_payload = json.dumps({
        "substrate": 255,
        "tests_total": total,
        "tests_passed": TESTS_PASSED,
        "tests_failed": TESTS_FAILED,
        "uc26_release_date": "2026-05-14",
        "timestamp": int(time.time()),
    }, sort_keys=True)
    print(f"  Canonical seal: {hashlib.sha3_256(seal_payload.encode()).hexdigest()}")
    print("=" * 70)
    return TESTS_FAILED == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
