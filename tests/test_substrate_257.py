import asyncio
import subprocess
from pathlib import Path

import pytest

from substrate_257 import (
    CryptoExpressAdapter,
    HardwarePlatform,
    HardwareValidationFramework,
    LoongsonBoard,
    LoongsonValidationLab,
    PhysicalRunner,
    PhysicalRunnerLab,
)


WORKSPACE = Path(__file__).resolve().parents[1]


class TestPhysicalRunnerLab:
    def test_default_lab_has_three_physical_runners(self):
        lab = PhysicalRunnerLab.default_lab()
        assert len(lab.runners) == 3
        assert "self-hosted-rpi4-tpm" in lab.runners
        assert "self-hosted-x86-tpm" in lab.runners

    def test_runner_labels_include_tpm(self):
        lab = PhysicalRunnerLab.default_lab()
        assert all("tpm2" in runner.labels for runner in lab.runners.values())

    def test_runner_matrix_is_github_actions_ready(self):
        matrix = PhysicalRunnerLab.default_lab().generate_github_runner_matrix()
        assert matrix[0]["runner"][0] == "self-hosted"
        assert {entry["architecture"] for entry in matrix} == {"arm64", "amd64"}

    def test_setup_manifest_has_lab_seal(self):
        manifest = PhysicalRunnerLab.default_lab().generate_setup_manifest()
        assert manifest["runner_count"] == 3
        assert len(manifest["lab_seal"]) == 64

    def test_heartbeat_marks_runner_online(self):
        lab = PhysicalRunnerLab.default_lab()
        runner = lab.record_runner_heartbeat("self-hosted-rpi5-tpm")
        assert runner.status == "online"
        assert lab.get_lab_report()["online_runners"] == ["self-hosted-rpi5-tpm"]

    def test_unknown_runner_fails(self):
        with pytest.raises(RuntimeError, match="Unknown runner"):
            PhysicalRunnerLab.default_lab().record_runner_heartbeat("missing")

    def test_register_custom_runner(self):
        lab = PhysicalRunnerLab.default_lab()
        lab.register_runner(
            PhysicalRunner(
                runner_id="self-hosted-loongson-3a5000",
                labels=["self-hosted", "linux", "loongarch64", "loongson"],
                platform="loongson-3a5000",
                architecture="loongarch64",
                device_ip="192.168.57.150",
                tpm_required=False,
                image_artifact="arkhe-core-loongarch64",
            )
        )
        assert lab.get_lab_report()["runner_count"] == 4


class TestHardwareValidationFramework:
    def test_pi4_validation_passes_in_dry_run(self):
        framework = HardwareValidationFramework(
            HardwarePlatform.RASPBERRY_PI_4,
            "Raspberry Pi 4B + TPM2 HAT",
        )
        report = asyncio.run(framework.run_full_validation())
        assert report.overall_success
        assert report.tpm_result.tpm_version == "2.0"
        assert len(report.temporal_chain_seal) == 64

    def test_pi5_validation_collects_memory_metric(self):
        report = asyncio.run(
            HardwareValidationFramework(
                HardwarePlatform.RASPBERRY_PI_5,
                "Raspberry Pi 5 + TPM2 HAT",
            ).run_full_validation()
        )
        assert report.performance_metrics["memory_mb"] == 8192.0

    def test_x86_validation_records_measured_boot(self):
        report = asyncio.run(
            HardwareValidationFramework(
                HardwarePlatform.X86_64_DISCRETE_TPM,
                "Generic PC with discrete TPM",
            ).run_full_validation()
        )
        assert report.boot_result.measured_boot_verified
        assert report.constitutional_result.overall_compliance

    def test_report_to_dict_serializes_platform_value(self):
        report = asyncio.run(
            HardwareValidationFramework(HardwarePlatform.INTEL_NUC_VTPM, "Intel NUC vTPM").run_full_validation()
        )
        payload = report.to_dict()
        assert payload["platform"] == "intel-nuc-vtpm"
        assert "duration_seconds" in payload

    def test_loongson_hardware_platform_profile_exists(self):
        report = asyncio.run(
            HardwareValidationFramework(HardwarePlatform.LOONGSON_3A5000, "Loongson 3A5000").run_full_validation()
        )
        assert report.performance_metrics["cpu_cores"] == 4.0
        assert report.overall_success

    def test_ibm_z_hardware_platform_profile_exists(self):
        report = asyncio.run(
            HardwareValidationFramework(HardwarePlatform.IBM_Z15, "IBM z15").run_full_validation()
        )
        assert report.performance_metrics["memory_mb"] == 65536.0
        assert report.power_metrics["power_draw_watts"] == 250.0


class TestCryptoExpress:
    def test_capabilities_include_cpacf_and_crypto_express(self):
        cap = CryptoExpressAdapter().detect_capabilities()
        assert cap.cpacf_enabled
        assert cap.crypto_express_enabled
        assert "Dilithium3" in cap.pqc_algorithms
        assert len(cap.canonical_seal) == 64

    def test_dilithium_operation_is_accelerated(self):
        op = CryptoExpressAdapter().sign_dilithium3(b"model assertion")
        assert op.algorithm == "Dilithium3"
        assert op.accelerated
        assert op.duration_us < 820
        assert len(op.canonical_seal) == 64

    def test_kyber_operation_is_accelerated(self):
        op = CryptoExpressAdapter().encapsulate_kyber768(b"arkhe session")
        assert op.operation_type == "encapsulate"
        assert op.algorithm == "Kyber768"
        assert op.input_sha3_256

    def test_unsupported_algorithm_fails(self):
        with pytest.raises(RuntimeError, match="Unsupported"):
            CryptoExpressAdapter().run_pqc_operation("Falcon1024", "sign", b"x")

    def test_acceleration_report_counts_operations(self):
        adapter = CryptoExpressAdapter()
        adapter.sign_dilithium3(b"a")
        adapter.encapsulate_kyber768(b"b")
        report = adapter.get_acceleration_report()
        assert report["operations_run"] == 2
        assert report["accelerated_operations"] == 2
        assert len(report["canonical_seal"]) == 64


class TestLoongsonValidation:
    def test_default_lab_has_3a5000_and_3c5000(self):
        lab = LoongsonValidationLab.default_lab()
        assert {board.model for board in lab.boards.values()} == {"3A5000", "3C5000"}

    def test_validation_plan_has_sovereign_checks(self):
        plan = LoongsonValidationLab.default_lab().generate_validation_plan()
        assert "u_boot_signature" in plan["checks"]
        assert len(plan["canonical_seal"]) == 64

    def test_validate_3a5000_board(self):
        lab = LoongsonValidationLab.default_lab()
        result = lab.validate_board("loongson-3a5000-lab", "arkhe-core-26-loongarch64.img")
        assert result["overall_success"]
        assert result["model"] == "3A5000"
        assert result["sovereign_tech"]

    def test_validate_3c5000_board(self):
        lab = LoongsonValidationLab.default_lab()
        result = lab.validate_board("loongson-3c5000-lab", "arkhe-core-26-loongarch64-server.img")
        assert result["phi_c"] > 0.97
        assert len(result["canonical_seal"]) == 64

    def test_unknown_loongson_board_fails(self):
        with pytest.raises(RuntimeError, match="Unknown Loongson board"):
            LoongsonValidationLab.default_lab().validate_board("unknown", "image.img")

    def test_lab_report_records_validations(self):
        lab = LoongsonValidationLab.default_lab()
        lab.validate_board("loongson-3a5000-lab", "image.img")
        report = lab.get_lab_report()
        assert report["board_count"] == 2
        assert report["validated_boards"] == ["loongson-3a5000-lab"]

    def test_custom_loongson_board_registers(self):
        lab = LoongsonValidationLab.default_lab()
        lab.register_board(LoongsonBoard(board_id="loongson-edge", model="3A5000", memory_gb=32))
        assert "loongson-edge" in lab.boards


class TestSubstrate257Artifacts:
    def test_enterprise_config_exists(self):
        config = WORKSPACE / "substrate_257" / "platform_config_enterprise.yaml"
        text = config.read_text(encoding="utf-8")
        assert "loongson-3a5000" in text
        assert "cpacf: true" in text
        assert "crypto_express: true" in text

    def test_workflow_has_hardware_validation_job(self):
        workflow = (WORKSPACE / ".github" / "workflows" / "arkhe-build.yml").read_text(encoding="utf-8")
        assert "hardware-validation:" in workflow
        assert "self-hosted, linux, arm64, rpi4, tpm2" in workflow
        assert "X86_64_DISCRETE_TPM" in workflow

    def test_workflow_keeps_enterprise_architectures(self):
        workflow = (WORKSPACE / ".github" / "workflows" / "arkhe-build.yml").read_text(encoding="utf-8")
        assert "loongarch64" in workflow
        assert "s390x" in workflow
        assert "hardware_validation" in workflow

    def test_substrate_257_package_exports_all_facades(self):
        import substrate_257

        assert "CryptoExpressAdapter" in substrate_257.__all__
        assert "PhysicalRunnerLab" in substrate_257.__all__
        assert "LoongsonValidationLab" in substrate_257.__all__

    def test_rpi_flash_script_has_destructive_guard(self):
        script = (WORKSPACE / "flash_arkhe_rpi.sh").read_text(encoding="utf-8")
        assert "ARKHE_FLASH_CONFIRM=YES" in script
        assert "ARKHE_FLASH_DRY_RUN" in script
        assert "Target is not a block device" in script

    def test_rpi_flash_script_syntax(self):
        result = subprocess.run(
            ["bash", "-n", "flash_arkhe_rpi.sh"],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert result.returncode == 0, result.stderr

    def test_rpi_flash_script_dry_run_generates_report(self, tmp_path):
        scratch = WORKSPACE / "build" / "pytest_tmp" / "flash_script"
        scratch.mkdir(parents=True, exist_ok=True)
        image = scratch / "arkhe-core-26-arm64.img"
        report = scratch / "flash-report.json"
        image.write_bytes(b"arkhe-test-image")
        result = subprocess.run(
            [
                "bash",
                "-lc",
                "ARKHE_FLASH_DRY_RUN=1 ARKHE_FLASH_REPORT=build/pytest_tmp/flash_script/flash-report.json "
                "./flash_arkhe_rpi.sh build/pytest_tmp/flash_script/arkhe-core-26-arm64.img /dev/not-real",
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert report.exists()
        assert '"flash_verify": true' in report.read_text(encoding="utf-8")
