import hashlib
import math

from substrates.substrate_385_unification.theory_experiment_unifier import (
    C,
    EXPERIMENT_384,
    PHI,
    Severity,
    THEORY_382,
    TheoryExperimentUnifier,
    main,
    write_markdown_report,
)


def _module(unifier, name):
    return next(result for result in unifier.results if result.module == name)


def test_constants_and_source_snapshots_are_registered():
    assert THEORY_382["scoop"]["field_tesla"] == 12.57
    assert EXPERIMENT_384["scoop"]["field_milli_tesla"] == 12.566
    assert EXPERIMENT_384["wormhole"]["anomalous_halos"] == 5
    assert math.isclose(PHI, 1.618033988749895)


def test_unification_accounting_matches_decree_shape():
    unifier = TheoryExperimentUnifier()
    unifier.run_unification()
    report = unifier.build_report()

    assert report.total_checks == 20
    assert report.passed_checks == 19
    assert report.warnings == 1
    assert report.phi_c == 0.95
    assert report.modules["385-STRANGELET-UNIFICATION"] == {"checks": 4, "pass": 3, "warn": 1, "phi_c": 0.75}
    assert report.modules["385-CONSTITUTIONAL-INVARIANTS"] == {"checks": 4, "pass": 4, "warn": 0, "phi_c": 1.0}


def test_scoop_unification_adjustments_and_energy_recalc():
    unifier = TheoryExperimentUnifier()
    unifier.run_unification()
    scoop = _module(unifier, "385-SCOOP-UNIFICATION")

    scale = next(det for inv, _, _, det in scoop.checks if inv == "U1_SCALE_SIMILITUDE")
    fem = next(det for inv, _, _, det in scoop.checks if inv == "U2_FEM_CORRECTION")
    energy = next(det for inv, _, _, det in scoop.checks if inv == "U4_ENERGY_RECALC")

    assert math.isclose(scale["extrapolated_T"], 12_566.0)
    assert math.isclose(scale["ratio"], 999.6817820206842)
    assert math.isclose(fem["adjusted_efficiency"], 0.833)
    assert math.isclose(unifier.adjustments["scoop_efficiency"], 0.833)
    assert energy["recalculated_J"] > energy["theory_J"]


def test_wormhole_detector_and_invariant_bridges():
    unifier = TheoryExperimentUnifier()
    unifier.run_unification()

    wormhole = _module(unifier, "385-WORMHOLE-UNIFICATION")
    detector = _module(unifier, "385-DETECTOR-UNIFICATION")
    invariants = _module(unifier, "385-CONSTITUTIONAL-INVARIANTS")

    rate = next(det for inv, _, _, det in wormhole.checks if inv == "U5_SIGNATURE_RATE")
    sensitivity = next(det for inv, _, _, det in detector.checks if inv == "U9_SENSITIVITY_ACCURACY")
    features = next(det for inv, _, _, det in detector.checks if inv == "U11_FEATURE_MATCH")
    golden = next(det for inv, _, _, det in invariants.checks if inv == "I4_GOLDEN_RATIO")

    assert math.isclose(rate["observed_rate"], 1 / 300)
    assert math.isclose(rate["predicted_rate"], 0.003)
    assert math.isclose(sensitivity["unified"], math.sqrt(0.78 * 0.94))
    assert features["exact_match"] is True
    assert math.isclose(golden["ratio"], PHI)


def test_strangelet_warn_and_relativistic_isp_cap():
    unifier = TheoryExperimentUnifier()
    unifier.run_unification()
    strangelet = _module(unifier, "385-STRANGELET-UNIFICATION")

    isp = next(det for inv, _, _, det in strangelet.checks if inv == "U14_ISP_ENERGY")
    yield_check = next((sev, det) for inv, sev, _, det in strangelet.checks if inv == "U15_YIELD_STATISTICS")

    assert math.isclose(isp["velocity_m_s"], 0.999 * C)
    assert isp["calculated_isp"] < 31_000_000
    assert yield_check[0] == Severity.WARN
    assert yield_check[1]["collisions_needed"] == 100_000_000
    assert yield_check[1]["confinement_status"] == "unverified"


def test_unification_proofs_verify_hash_signature():
    unifier = TheoryExperimentUnifier()
    unifier.run_unification()

    for result in unifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.platform_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_unification_report_and_main(tmp_path):
    path = write_markdown_report(tmp_path / "substrate_385_theory_experiment_report.md")
    text = path.read_text(encoding="utf-8")

    assert "SUBSTRATO 385" in text
    assert "Phi_C: 0.950000" in text
    assert "385-STRANGELET-UNIFICATION" in text
    assert main()["substrate"] == 385
