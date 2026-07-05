import hashlib
import math

from substrates.substrate_382.wormhole_sim import WormholeSimVerifier, main as wormhole_main, write_markdown_report as write_wormhole
from substrates.substrate_382.detector_integration import Detector382Verifier, main as detector_main, write_markdown_report as write_detector
from substrates.substrate_382.quark_strangelet import Quark382Verifier, main as quark_main, write_markdown_report as write_quark


def _assert_proofs(verifier):
    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_wormhole_sim_detail_accounting_and_highlights():
    verifier = WormholeSimVerifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 6
    assert report.passed_checks == 5
    assert report.warnings == 1
    assert report.phi_c == 0.833333
    assert report.highlights["stability_score"] > 0.99
    assert math.isclose(report.highlights["traversal_years"], 211.5)
    _assert_proofs(verifier)


def test_detector_detail_accounting_and_sensor_fusion():
    verifier = Detector382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 6
    assert report.passed_checks == 5
    assert report.warnings == 1
    assert report.phi_c == 0.833333
    assert 0.5 < report.highlights["confidence"] < 0.6
    assert report.highlights["avg_latency_ms"] < 200
    _assert_proofs(verifier)


def test_quark_detail_accounting_and_efficiency():
    verifier = Quark382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 6
    assert report.passed_checks == 4
    assert report.warnings == 2
    assert report.phi_c == 0.666667
    assert report.highlights["pulse_energy_j"] == 9_600_000.0
    assert 0.10 < report.highlights["fraction_of_annihilation"] < 0.11
    _assert_proofs(verifier)


def test_branch_markdown_reports_are_written(tmp_path):
    wormhole = write_wormhole(tmp_path / "wormhole.md")
    detector = write_detector(tmp_path / "detector.md")
    quark = write_quark(tmp_path / "quark.md")

    assert "382-WORMHOLE-SIM" in wormhole.read_text(encoding="utf-8")
    assert "382-DETECTOR" in detector.read_text(encoding="utf-8")
    assert "382-QUARK" in quark.read_text(encoding="utf-8")


def test_branch_mains_return_reports():
    assert wormhole_main()["substrate"] == "382-WORMHOLE-SIM"
    assert detector_main()["substrate"] == "382-DETECTOR"
    assert quark_main()["substrate"] == "382-QUARK"
