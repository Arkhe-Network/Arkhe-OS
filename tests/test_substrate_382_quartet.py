import hashlib
import math

from substrates.substrate_382.quartet import Quartet382Verifier, Severity, main, write_markdown_report


def _module(verifier, name):
    return next(result for result in verifier.results if result.module == name)


def test_quartet_accounting_matches_canonical_decree():
    verifier = Quartet382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 17
    assert report.passed_checks == 15
    assert report.warnings == 2
    assert report.phi_c == 0.882353
    assert report.components["382-SCOOP"] == {"checks": 4, "pass": 3, "warn": 1, "phi_c": 0.75}
    assert report.components["382-WORMHOLE-SIM"] == {"checks": 5, "pass": 5, "warn": 0, "phi_c": 1.0}
    assert report.components["382-DETECTOR"] == {"checks": 4, "pass": 4, "warn": 0, "phi_c": 1.0}
    assert report.components["382-QUARK"] == {"checks": 4, "pass": 3, "warn": 1, "phi_c": 0.75}


def test_quartet_scoop_values_and_cooling_warning():
    verifier = Quartet382Verifier()
    verifier.run()
    scoop = _module(verifier, "382-SCOOP")

    field = next(det for inv, _, _, det in scoop.checks if inv == "MAGNETIC_FIELD")
    area = next(det for inv, _, _, det in scoop.checks if inv == "COLLECTION_AREA")
    power = next((sev, det) for inv, sev, _, det in scoop.checks if inv == "DISSIPATED_POWER")

    assert math.isclose(field["field_t"], 12.566370614359172, rel_tol=1e-12)
    assert math.isclose(area["area_m2"], math.pi * 1e12, rel_tol=1e-12)
    assert power[0] == Severity.WARN
    assert power[1]["power_w"] == 1.0e9


def test_quartet_wormhole_values_are_canonical():
    verifier = Quartet382Verifier()
    verifier.run()
    wormhole = _module(verifier, "382-WORMHOLE-SIM")

    f_qt = next(det for inv, _, _, det in wormhole.checks if inv == "FQT_FUNCTION")
    transit = next(det for inv, _, _, det in wormhole.checks if inv == "TRANSIT")
    tidal = next(det for inv, _, _, det in wormhole.checks if inv == "TIDAL")

    assert f_qt["formula"] == "Q + 0.3T"
    assert f_qt["f_qt"] == 0.51
    assert math.isclose(transit["years"], 211.5)
    assert math.isclose(tidal["tidal_g"], 2.71)


def test_quartet_detector_and_quark_values():
    verifier = Quartet382Verifier()
    verifier.run()
    detector = _module(verifier, "382-DETECTOR")
    quark = _module(verifier, "382-QUARK")

    halos = next(det for inv, _, _, det in detector.checks if inv == "HALOS")
    sensitivity = next(det for inv, _, _, det in detector.checks if inv == "SENSITIVITY")
    thrust = next(det for inv, _, _, det in quark.checks if inv == "THRUST")
    confinement = next((sev, det) for inv, sev, _, det in quark.checks if inv == "STRANGENESS_CONFINEMENT")

    assert halos["halos"] == 48
    assert sensitivity["sensitivity"] == 0.78
    assert thrust["thrust_n"] == 8.82e6
    assert confinement[0] == Severity.WARN
    assert confinement[1]["verified"] is False


def test_quartet_proofs_verify_hash_signature():
    verifier = Quartet382Verifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_quartet_report_and_main(tmp_path):
    path = write_markdown_report(tmp_path / "substrate_382_quartet_report.md")
    text = path.read_text(encoding="utf-8")

    assert "SUBSTRATO 382-QUARTETO" in text
    assert "Phi_C: 0.882353" in text
    assert "382-WORMHOLE-SIM: 5/5 PASS" in text
    assert main()["substrate"] == "382-QUARTETO"
