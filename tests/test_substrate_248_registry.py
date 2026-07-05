from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "substrate_248" / "powershell" / "ArkheRegistry.psm1"
MANIFEST = ROOT / "substrate_248" / "powershell" / "ArkheRegistry.psd1"


def test_registry_module_exists():
    assert MODULE.exists()
    assert MANIFEST.exists()


def test_required_cmdlets_are_exported():
    text = MODULE.read_text(encoding="utf-8")
    required = {
        "Get-ArkheRegistry",
        "Set-ArkheRegistry",
        "Get-ArkhePhiC",
        "Get-ArkheAgentStatus",
        "Export-ArkheRegistryToTemporalChain",
        "Update-ArkheRegistrySeal",
        "Sync-ArkheCrossPlatformConfig",
        "Get-ArkheEffectivePolicy",
        "Set-ArkheGroupPolicy",
        "Register-ArkheMsiVersion",
        "Restore-ArkheMsiVersion",
    }

    for name in required:
        assert re.search(rf"function\s+{re.escape(name)}\b", text)
        assert f'"{name}"' in text


def test_policy_and_registry_roots_are_canonical():
    text = MODULE.read_text(encoding="utf-8")
    assert 'HKLM:\\SOFTWARE\\ARKHE' in text
    assert 'HKLM:\\SOFTWARE\\Policies\\ARKHE' in text
    assert '"/etc/arkhe"' in text


def test_msi_snapshots_are_registered_under_installer_key():
    text = MODULE.read_text(encoding="utf-8")
    assert 'Installer\\Snapshots\\$Version' in text
    assert '"CurrentVersion"' in text
    assert '"RollbackUtc"' in text


def test_registry_key_creation_is_non_destructive():
    text = MODULE.read_text(encoding="utf-8")
    assert "function Ensure-ArkheRegistryKey" in text
    assert "New-Item -Path $target -Force" not in text


def test_no_deprecated_utcnow_usage():
    text = MODULE.read_text(encoding="utf-8")
    assert "UtcNow" in text
    assert "datetime.utcnow" not in text
