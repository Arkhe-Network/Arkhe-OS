from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "build" / "arkhe_build.py"
CONFIG = ROOT / "build" / "arkhe_build_targets.json"


def test_build_orchestrator_exists():
    assert SCRIPT.exists()
    assert CONFIG.exists()


def test_cross_platform_targets_are_declared():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    targets = set(data["targets"])
    assert "x86_64-unknown-linux-gnu" in targets
    assert "aarch64-unknown-linux-gnu" in targets
    assert "x86_64-pc-windows-msvc" in targets
    assert "aarch64-pc-windows-msvc" in targets
    assert "x86_64-unknown-freebsd" in targets


def test_package_formats_are_declared():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert set(data["package_formats"]) == {"deb", "rpm", "msi", "pkg"}


def test_orchestrator_has_expected_subcommands():
    text = SCRIPT.read_text(encoding="utf-8")
    for command in ["inventory", "build", "test", "package-grammars", "package"]:
        assert f'"{command}"' in text


def test_production_ops_artifacts_exist():
    required = [
        "Makefile",
        "Dockerfile",
        "packaging/build_deb.sh",
        "packaging/build_rpm.sh",
        "packaging/build_msi.ps1",
        "packaging/build_freebsd_pkg.sh",
        "deploy/deploy_test_environment.sh",
        "deploy/docker-swarm/federated-aggregators.yml",
        "observability/prometheus/arkhe-prometheus.yml",
        "observability/grafana/arkhe-dashboard.json",
        "security/hsm/pkcs11-dilithium-pilot.toml",
        "ops/backup/arkhe_backup.sh",
        "ops/backup/Arkhe-ReFSSnapshot.ps1",
        "docs/RUNBOOK_OPERATIONS.md",
        "docs/VALIDATION_CERTIFICATION.md",
    ]
    for relative in required:
        assert (ROOT / relative).exists()


def test_dockerfile_uses_normalized_out_directory():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "/src/out" in text
    assert "COPY --from=package-builder /src/out/ /opt/arkhe/" in text


def test_deb_postinst_is_systemd_tolerant():
    text = (ROOT / "packaging/build_deb.sh").read_text(encoding="utf-8")
    assert "systemctl daemon-reload || true" in text
    assert "systemctl enable arkhe-agi.service || true" in text
    assert "systemctl start arkhe-agi.service || true" in text
