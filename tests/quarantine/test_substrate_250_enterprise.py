from pathlib import Path

from substrate_250.gpo.multi_domain_engine import MultiDomainGPOEngine
from substrate_250.ml.config_optimizer import MLConfigOptimizer, PhiCRecord
from substrate_250.siem.siem_forwarder import ArkheEvent, EventSeverity, SIEMConfig, SIEMForwarder, SIEMTarget


def test_siem_forwarder_writes_splunk_and_qradar_payloads(tmp_path: Path):
    event = ArkheEvent(
        event_id=3001,
        event_name="RegistryValueModified",
        severity=EventSeverity.MEDIUM,
        raw_message="registry_path=HKLM\\SOFTWARE\\ARKHE value_name=BusPort phi_c_before=0.91 phi_c_after=0.94",
        registry_path="HKLM\\SOFTWARE\\ARKHE",
        value_name="BusPort",
        phi_c_before=0.91,
        phi_c_after=0.94,
    )
    forwarder = SIEMForwarder(tmp_path, SIEMConfig(targets=SIEMTarget.BOTH))
    result = forwarder.forward([event])

    assert result.events_forwarded == 2
    assert result.temporal_chain_seal
    payload = (tmp_path / "enterprise_siem.jsonl").read_text(encoding="utf-8")
    assert "splunk_hec" in payload
    assert "CEF:0|ARKHE|ASI|250.1.0|3001" in payload


def test_siem_event_parser_maps_known_event_id():
    event = SIEMForwarder.from_event_log_message(
        3004,
        "registry_path=HKLM value_name=PhiC phi_c_before=0.96 phi_c_after=0.82 constitutional_check=warning",
    )
    assert event.event_name == "PhiCThresholdViolation"
    assert event.severity == EventSeverity.HIGH
    assert event.phi_c_after == 0.82


def test_ml_optimizer_recommends_best_historical_config():
    optimizer = MLConfigOptimizer()
    history = [
        PhiCRecord(1, {"Network/BusPort": 8080, "Service/ThreadPoolSize": 16}, 0.91),
        PhiCRecord(2, {"Network/BusPort": 8443, "Service/ThreadPoolSize": 24}, 0.97),
    ]
    recommendations = optimizer.recommend(history)

    assert recommendations
    assert recommendations[0]["constitutional_check"] == "passed"
    assert recommendations[0]["expected_phi_c"] == 0.97
    assert recommendations[0]["temporal_chain_seal"]


def test_ml_optimizer_dry_run_has_rollback_plan():
    optimizer = MLConfigOptimizer()
    recommendation = optimizer.recommend(
        [PhiCRecord(1, {"Network/BusPort": 8443, "Service/ThreadPoolSize": 24}, 0.97)]
    )[0]
    result = optimizer.apply_dry_run(recommendation, current_phi_c=0.9)
    assert result["accepted"] is True
    assert "Restore" in result["rollback_plan"]


def test_multi_domain_gpo_policy_applies_with_partner_rejection():
    engine = MultiDomainGPOEngine("arkhe.org")
    policy = engine.create_policy(
        "ARKHE-ASI-Enterprise-Policy",
        ["production.arkhe.org", "partner.arkhe.org"],
        {"Security/FipsMode": 1, "Network/BusPort": 8443},
        enforcement_level="enforced",
    )
    results = engine.apply_policy_dry_run(policy)

    assert policy.temporal_chain_seal
    assert any(result["target_domain"] == "partner.arkhe.org" and result["values_rejected"] == 1 for result in results)
    assert engine.status()["applications"] == 4


def test_powershell_enterprise_module_exists():
    root = Path(__file__).resolve().parents[1]
    module = root / "substrate_250/powershell/ArkheEnterprise.psm1"
    manifest = root / "substrate_250/powershell/ArkheEnterprise.psd1"
    assert module.exists()
    assert manifest.exists()
    assert "Set-ArkheSIEMConfig" in module.read_text(encoding="utf-8")
