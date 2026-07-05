from pathlib import Path

from substrate_249.common import ConfigValue
from substrate_249.gpo.gpo_integration import GpoIntegrationEngine, GpoPolicyValue, PolicyEnforcement
from substrate_249.gpo.multi_domain import DomainTarget, MultiDomainGpoPlanner
from substrate_249.ml.config_optimizer import ConfigOptimizer, PhiCObservation
from substrate_249.msi.upgrade_engine import MsiUpgradeEngine
from substrate_249.siem.forwarder import AuditEvent, SiemForwarder
from substrate_249.sync.cross_platform_sync import (
    ConflictResolution,
    CrossPlatformSyncEngine,
    SyncPolicy,
    seed_store,
)


def test_cross_platform_sync_resolves_by_phi_c(tmp_path: Path):
    windows = tmp_path / "windows.json"
    linux = tmp_path / "linux.json"
    seed_store(
        windows,
        {"Network/BusPort": ConfigValue("Network/BusPort", 8080, phi_c_score=0.91, last_modified=1)},
    )
    seed_store(
        linux,
        {"Network/BusPort": ConfigValue("Network/BusPort", 8081, phi_c_score=0.98, last_modified=2)},
    )
    engine = CrossPlatformSyncEngine(
        windows,
        linux,
        SyncPolicy(conflict_resolution=ConflictResolution.PHI_C_WEIGHTED),
    )
    result = engine.run_sync_cycle()
    assert result.conflicts_detected == 1
    assert result.conflicts_resolved == 1
    assert result.overall_phi_c >= 0.9
    assert "8081" in windows.read_text(encoding="utf-8")


def test_gpo_applies_and_rejects_unconstitutional_policy(tmp_path: Path):
    engine = GpoIntegrationEngine(tmp_path / "local.json", tmp_path / "policy.json")
    policies = [
        GpoPolicyValue("Security/FipsMode", 1, "REG_DWORD", PolicyEnforcement.ENFORCED),
        GpoPolicyValue("PhiC/Composite", "1.0", "REG_SZ", PolicyEnforcement.ENFORCED),
    ]
    result = engine.apply_gpo_policies(policies)
    assert result.values_applied == 1
    assert result.values_rejected == 1
    assert result.temporal_chain_seal


def test_msi_upgrade_and_rollback(tmp_path: Path):
    engine = MsiUpgradeEngine(tmp_path, current_version="248.2.0")
    upgrade = engine.perform_upgrade("249.1.0")
    assert upgrade.success
    assert upgrade.rollback_available
    rollback = engine.perform_rollback(upgrade.backup)
    assert rollback.success
    assert rollback.version_to == "248.2.0"


def test_siem_forwarder_writes_sealed_envelopes(tmp_path: Path):
    forwarder = SiemForwarder(tmp_path / "siem.jsonl", target="qradar-leef")
    result = forwarder.forward([AuditEvent(3001, "ArkheRegistry", "value changed")])
    assert result["events_forwarded"] == 1
    assert "canonical_seal" in (tmp_path / "siem.jsonl").read_text(encoding="utf-8")


def test_config_optimizer_recommends_best_phi_c():
    optimizer = ConfigOptimizer()
    result = optimizer.recommend(
        [
            PhiCObservation(8080, 5000, 300, 0.91),
            PhiCObservation(8081, 5001, 120, 0.97),
        ]
    )
    assert result["Network/BusPort"] == 8081
    assert result["expected_phi_c"] == 0.97
    assert result["canonical_seal"]


def test_multi_domain_gpo_plan_has_temporal_seal():
    planner = MultiDomainGpoPlanner()
    plan = planner.build_plan(
        [DomainTarget("arkhe.local", "corp.arkhe.local", "OU=Servers")],
        [GpoPolicyValue("Security/PqcEnabled", 1)],
    )
    assert plan.plan_id
    assert plan.temporal_chain_seal


def test_powershell_advanced_module_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "substrate_249/powershell/ArkheAdvanced.psm1").exists()
    assert (root / "substrate_249/powershell/ArkheAdvanced.psd1").exists()
