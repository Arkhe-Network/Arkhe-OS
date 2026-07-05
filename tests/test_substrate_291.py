import json

from substrate_291 import (
    ArkhePacketFilter,
    EmbeddedFirmwareSimulator,
    FirmwareIntegrity,
    LinkMetrics,
    LinkType,
    NISTAccreditedAuditPlan,
    PQCHandshakePolicy,
    ProductionLoadProfile,
    RegulatedProductionGate,
    SatelliteRegionExpansionPlanner,
)


def test_link_metrics_good_wifi_exceeds_ghost_threshold():
    metrics = LinkMetrics(rssi_dbm=-45, snr_db=35, latency_ms=5, packet_loss=0.01, security="WPA3")
    assert metrics.quality_phi_c() >= 0.577553
    assert metrics.quality_phi_c() < 1.0


def test_link_metrics_weak_open_link_fails_threshold():
    metrics = LinkMetrics(rssi_dbm=-88, snr_db=4, latency_ms=120, packet_loss=0.35, security="OPEN")
    assert metrics.quality_phi_c() < 0.577553


def test_packet_filter_forwards_good_frame_and_seals():
    packet_filter = ArkhePacketFilter("router-openwrt-01", LinkType.WIFI)
    decision = packet_filter.evaluate_frame(
        LinkMetrics(rssi_dbm=-45, snr_db=35, latency_ms=5, packet_loss=0.01, security="WPA3"),
        b"GET /index.html HTTP/1.1",
    )
    assert decision.allowed
    assert decision.reason == "FORWARD"
    assert len(decision.temporal_seal) == 16
    assert packet_filter.get_statistics()["packets_forwarded"] == 1


def test_packet_filter_drops_bad_frame():
    packet_filter = ArkhePacketFilter("bt-driver-01", LinkType.BLUETOOTH)
    decision = packet_filter.evaluate_frame(
        LinkMetrics(rssi_dbm=-90, snr_db=2, latency_ms=180, packet_loss=0.6, security="OPEN"),
        b"AT+CMD",
    )
    assert not decision.allowed
    assert decision.reason == "GHOST_VIOLATION"
    assert packet_filter.get_statistics()["packets_dropped"] == 1


def test_evaluate_quadro_compatibility_alias():
    packet_filter = ArkhePacketFilter("modem-01", LinkType.MODEM)
    allowed, reason = packet_filter.evaluate_quadro(
        LinkMetrics(rssi_dbm=-50, snr_db=34, latency_ms=10, packet_loss=0.0, security="QKD"),
        b"\x01\x02",
    )
    assert allowed
    assert "FORWARD" in reason


def test_firmware_integrity_boot_check_passes_for_matching_hash():
    blob = b"firmware-v291"
    integrity = FirmwareIntegrity(blob)
    assert integrity.boot_check()
    assert len(integrity.firmware_hash) == 64


def test_firmware_integrity_boot_check_fails_for_mismatch():
    integrity = FirmwareIntegrity(b"firmware-v291", expected_hash="0" * 64)
    assert not integrity.boot_check()


def test_firmware_manifest_verification():
    integrity = FirmwareIntegrity(b"firmware-v291")
    assert integrity.verify_manifest(
        {"integrity_algorithm": "SHA3-256", "firmware_sha3_256": integrity.firmware_hash}
    )
    assert not integrity.verify_manifest(
        {"integrity_algorithm": "SHA256", "firmware_sha3_256": integrity.firmware_hash}
    )


def test_zeroize_keys_overwrites_bytearray():
    key_material = bytearray(b"secret-key")
    integrity = FirmwareIntegrity(b"firmware")
    assert integrity.zeroize_keys(key_material)
    assert all(byte == 0 for byte in key_material)


def test_pqc_handshake_policy_accepts_supported_peer():
    policy = PQCHandshakePolicy()
    report = policy.negotiate(["ML-KEM-768", "ML-DSA-65"], firmware_ok=True)
    assert report["allowed"]
    assert len(report["handshake_seal"]) == 64


def test_pqc_handshake_policy_rejects_missing_capability():
    policy = PQCHandshakePolicy()
    report = policy.negotiate(["ML-KEM-768"], firmware_ok=True)
    assert not report["allowed"]


def test_embedded_firmware_simulator_report():
    report = EmbeddedFirmwareSimulator().run()
    assert report["substrate"] == "291"
    assert report["boot_check"]
    assert len(report["decisions"]) == 3
    assert any(not item["decision"]["allowed"] for item in report["decisions"])
    assert len(report["canonical_seal"]) == 64


def test_regulated_production_gate_rejects_raw_sensitive_high_risk_load():
    profile = ProductionLoadProfile(
        sector="government_intelligence",
        classification="secret",
        records_per_second=50_000,
        synthetic_or_tokenized=False,
        pii_present=True,
        secrets_present=True,
    )
    report = RegulatedProductionGate().evaluate(profile)
    assert report["high_risk"]
    assert not report["allowed_for_automation"]
    assert report["requires_human_authorization"]


def test_regulated_production_gate_accepts_tokenized_financial_fixture():
    profile = ProductionLoadProfile(
        sector="financial_services",
        classification="financial_sensitive",
        records_per_second=500,
        synthetic_or_tokenized=True,
        pii_present=False,
        secrets_present=False,
        redaction_proof="sha3:redacted",
    )
    report = RegulatedProductionGate().evaluate(profile)
    assert report["high_risk"]
    assert report["allowed_for_automation"]
    assert not report["requires_human_authorization"]


def test_nist_audit_plan_ready_with_baseline_artifacts():
    plan = NISTAccreditedAuditPlan()
    report = plan.build(plan.baseline_artifacts())
    assert report["ready_for_lab_intake"]
    assert report["provided_count"] == report["total_required"]
    assert len(report["canonical_seal"]) == 64


def test_nist_audit_plan_detects_missing_artifact():
    plan = NISTAccreditedAuditPlan()
    artifacts = plan.baseline_artifacts()
    del artifacts["entropy_assessment"]
    report = plan.build(artifacts)
    assert not report["ready_for_lab_intake"]
    assert "entropy_assessment" in report["missing_artifacts"]


def test_satellite_expansion_reaches_16_plus_regions():
    report = SatelliteRegionExpansionPlanner().generate_plan()
    assert report["region_count"] >= 16
    assert report["satellite_count"] == 6
    assert report["global_coverage_ready"]
    assert len(report["canonical_seal"]) == 64


def test_satellite_expansion_serializable():
    report = SatelliteRegionExpansionPlanner().generate_plan()
    assert isinstance(json.dumps(report), str)


def test_openwrt_skeleton_exists():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "substrate_291" / "openwrt_kmod_arkhe_constitutional.c"
    text = path.read_text(encoding="utf-8")
    assert "NF_INET_PRE_ROUTING" in text
    assert "ARKHE_GHOST_INVARIANT" in text
