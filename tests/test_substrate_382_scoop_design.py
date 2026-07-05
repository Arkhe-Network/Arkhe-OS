import hashlib
import math

from substrates.substrate_382.scoop_design import (
    AxionCapturePropulsion,
    MagneticSolenoidScoop,
    PrimakoffConversionModel,
    Scoop382Verifier,
    Severity,
    main,
    write_markdown_report,
)


def test_solenoid_field_matches_decree_values():
    scoop = MagneticSolenoidScoop()

    assert math.isclose(scoop.area_m2(), math.pi * 1e12, rel_tol=1e-12)
    assert math.isclose(scoop.internal_field_t(), 12.566370614359172, rel_tol=1e-12)
    assert math.isclose(scoop.surface_field_t(), 12.566370614359172, rel_tol=1e-12)
    assert math.isclose(scoop.field_at_radius_multiple_t(2.0), 3.141592653589793, rel_tol=1e-12)


def test_primakoff_canonical_rate_and_unit_boundary():
    primakoff = PrimakoffConversionModel()
    area = MagneticSolenoidScoop().area_m2()

    assert math.isclose(primakoff.axion_mass_gev(), 1e-15, rel_tol=1e-12)
    assert math.isclose(primakoff.axion_mass_kg(), 1.78266192e-42, rel_tol=1e-12)
    assert primakoff.effective_conversion_probability(area) < 1e-55
    assert math.isclose(primakoff.canonical_efficiency(), 6.149e-44, rel_tol=1e-12)


def test_capture_propulsion_outputs_match_canonical_scale():
    area = MagneticSolenoidScoop().area_m2()
    propulsion = AxionCapturePropulsion()

    assert math.isclose(propulsion.capture_rate_kg_s(area), 0.1883651567308853, rel_tol=1e-12)
    assert math.isclose(propulsion.output_power_w(area) / 1e12, 16929.0, rel_tol=1e-3)
    assert math.isclose(propulsion.thrust_n(area), 1.129e8, rel_tol=1e-3)
    assert propulsion.acceleration_g(area) > 11.0


def test_scoop_verifier_accounting_matches_decree():
    verifier = Scoop382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 11
    assert report.passed_checks == 9
    assert report.warnings == 2
    assert report.phi_c == 0.818182
    assert report.modules["ENGINEERING"]["phi_c"] == 1 / 3


def test_engineering_has_two_warns_no_failures():
    verifier = Scoop382Verifier()
    verifier.run()
    engineering = next(result for result in verifier.results if result.module == "ENGINEERING")

    assert sum(1 for _, sev, _, _ in engineering.checks if sev == Severity.WARN) == 2
    assert all(sev != Severity.FAIL for _, sev, _, _ in engineering.checks)


def test_scoop_proofs_verify_hash_signature():
    verifier = Scoop382Verifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_markdown_report_is_written(tmp_path):
    path = write_markdown_report(tmp_path / "substrate_382_scoop_report.md")

    text = path.read_text(encoding="utf-8")
    assert "SUBSTRATO 382-SCOOP" in text
    assert "Phi_C: 0.818182" in text
    assert "Axions are neutral" in text


def test_scoop_main_returns_report():
    report = main()

    assert report["substrate"] == "382-SCOOP"
    assert report["status"] == "CANONIZED_SPECULATIVE_AXION_SCOOP"
    assert report["total_checks"] == 11
