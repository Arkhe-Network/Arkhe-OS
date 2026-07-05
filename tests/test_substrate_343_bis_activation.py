import pytest

from substrates.substrate_342.orkut_labs_dev import GHOST, LOOPSEAL, GAP_MAX
from substrates.substrate_343_bis import (
    PTT343_ACTIVATION_SEAL,
    PTT343_PORTAL_GATES,
    SUBSTRATE_271_LATENCY_LIMIT_MS,
    activation_phi_c,
    activation_report_payload,
    activation_statistics,
    build_activation_packets,
    build_activation_report,
    generate_activation_configs,
    render_activation_report,
    write_activation_artifacts,
)


def test_activation_generates_100_packets_from_20_route_cycle():
    packets = build_activation_packets()

    assert len(packets) == 100
    assert packets[0]["src"] == "PG-NA"
    assert packets[0]["dst"] == "PG-SA"
    assert packets[0]["route_type"] == "STANDARD"
    assert packets[20]["src"] == packets[0]["src"]
    assert packets[20]["dst"] == packets[0]["dst"]
    assert all(packet["validated"] for packet in packets)


def test_long_haul_routes_are_compensated_by_loopseal():
    packets = build_activation_packets()
    compensated = [packet for packet in packets if packet["route_type"] == "COMPENSATED_LONG_HAUL"]
    standard = [packet for packet in packets if packet["route_type"] == "STANDARD"]

    assert len(compensated) == 40
    assert len(standard) == 60
    assert all(packet["distance_km"] > 10000 for packet in compensated)
    assert all(packet["optical_compensation"] == pytest.approx(LOOPSEAL) for packet in compensated)
    assert all(packet["optical_compensation"] == 1.0 for packet in standard)


def test_activation_statistics_match_decree():
    stats = activation_statistics(build_activation_packets())

    assert stats.avg_latency_ms == pytest.approx(33.193687344114835)
    assert stats.max_latency_ms == pytest.approx(47.296401557946936)
    assert stats.min_latency_ms == pytest.approx(18.768761390612074)
    assert stats.validated_count == 100
    assert stats.validated_rate == 1.0
    assert stats.compensated_routes == 40
    assert stats.standard_routes == 60


def test_activation_phi_c_matches_decree_and_invariants():
    stats = activation_statistics(build_activation_packets())
    phi_c = activation_phi_c(stats)

    assert phi_c.bruto == pytest.approx(1.6061366800090868)
    assert phi_c.normalizado == pytest.approx(0.7293341954855757)
    assert phi_c.normalizado > GHOST
    assert phi_c.normalizado > LOOPSEAL
    assert phi_c.normalizado < GAP_MAX


def test_portal_gates_and_vendor_configs_are_complete():
    assert len(PTT343_PORTAL_GATES) == 5
    assert {gate["gate"] for gate in PTT343_PORTAL_GATES} == {"PG-NA", "PG-SA", "PG-EU", "PG-AS", "PG-AF"}
    assert len(PTT343_PORTAL_GATES) * 2 == 10


def test_activation_config_templates_include_portal_extensions():
    configs = generate_activation_configs()

    assert set(configs) == {"PG-NA", "PG-SA", "PG-EU", "PG-AS", "PG-AF"}
    assert "router ospf 17" in configs["PG-NA"]["primary"]
    assert "community-set ARKHE-TEMPORAL" in configs["PG-NA"]["primary"]
    assert "protocols" in configs["PG-NA"]["backup"]
    assert "arkhe-portal fingerprint" in configs["PG-SA"]["primary"]
    assert "Vendor-specific template pending" in configs["PG-EU"]["primary"]


def test_activation_payload_and_report_are_serializable():
    payload = activation_report_payload()
    report = render_activation_report()

    assert payload["protocol"] == "PTT-343-ACT"
    assert payload["packet_count"] == 100
    assert payload["statistics"]["validated_rate"] == 1.0
    assert payload["empirical_status"] == "symbolic_speculative_model"
    assert "RELATORIO DE ATIVACAO" in report
    assert PTT343_ACTIVATION_SEAL in report


def test_write_activation_artifacts(tmp_path):
    paths = write_activation_artifacts(tmp_path)
    configs_dir = tmp_path / "substrato_343_bis_exp_act_configs"

    assert configs_dir.exists()
    assert len(list(configs_dir.iterdir())) == 10
    assert (tmp_path / "substrato_343_bis_exp_act_traffic.json").exists()
    assert (tmp_path / "substrato_343_bis_exp_act_report.txt").exists()
    assert paths["configs_dir"] == str(configs_dir)


def test_activation_report_converges():
    report = build_activation_report()

    assert report.packet_count == 100
    assert report.gates_count == 5
    assert report.generated_config_count == 10
    assert report.statistics.max_latency_ms < SUBSTRATE_271_LATENCY_LIMIT_MS
    assert report.statistics.validated_rate == 1.0
    assert all(report.invariants.values())
    assert report.converged
    assert report.activation_seal == PTT343_ACTIVATION_SEAL
