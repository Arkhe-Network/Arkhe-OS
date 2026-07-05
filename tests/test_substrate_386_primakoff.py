import hashlib
import math

from substrates.substrate_386_primakoff.primakoff_bench import (
    AxionBeamSimulator,
    HTSCoilPrototype,
    PrimakoffConversionBench,
    Severity,
    Substrate386PrimakoffVerifier,
    main,
    write_markdown_report,
)


def _module(verifier, name):
    return next(result for result in verifier.results if result.module == name)


def test_hts_coil_one_meter_geometry_and_field():
    coil = HTSCoilPrototype()

    assert coil.length_m == 1.0
    assert coil.turns == 10_000
    assert math.isclose(coil.magnetic_field_t(), 10.0, rel_tol=1e-12)
    assert math.isclose(coil.stored_energy_j(), 312_500.0, rel_tol=1e-12)
    assert coil.hoop_stress_mpa() < coil.allowable_stress_mpa


def test_axion_beam_is_explicitly_synthetic():
    beam = AxionBeamSimulator()
    spec = beam.spec()

    assert spec["energy_uev"] == 1.0
    assert spec["coupling_gev_inv"] == 1e-10
    assert spec["flux_per_second"] == 1e20
    assert spec["synthetic_source"] is True
    assert 2.4e8 < spec["photon_frequency_hz"] < 2.5e8


def test_primakoff_bench_counts_and_snr():
    bench = PrimakoffConversionBench()
    summary = bench.summary()

    assert math.isclose(summary["conversion_probability"], 1e-22, rel_tol=1e-12)
    assert math.isclose(summary["expected_signal_counts"], 6200.0, rel_tol=1e-12)
    assert summary["snr"] > 70.0
    assert summary["background_counts"] == 400.0


def test_substrate_386_accounting_and_warn_boundary():
    verifier = Substrate386PrimakoffVerifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 14
    assert report.passed_checks == 13
    assert report.warnings == 1
    assert report.phi_c == 0.928571
    assert report.highlights["field_t"] == 10.0
    assert report.highlights["expected_signal_counts"] == 6200.0

    beam_module = _module(verifier, "386-AXION-BEAM-SIM")
    boundary = next((sev, det) for inv, sev, _, det in beam_module.checks if inv == "AB4_SOURCE_BOUNDARY")
    assert boundary[0] == Severity.WARN
    assert boundary[1]["synthetic_source"] is True


def test_substrate_386_module_breakdown():
    verifier = Substrate386PrimakoffVerifier()
    verifier.run()

    expected = {
        "386-HTS-COIL": (4, 4, 0),
        "386-AXION-BEAM-SIM": (4, 3, 1),
        "386-PRIMAKOFF-CONVERSION": (4, 4, 0),
        "386-PUBLICATION": (2, 2, 0),
    }
    for module, (checks, passed, warnings) in expected.items():
        result = _module(verifier, module)
        assert len(result.checks) == checks
        assert sum(1 for _, sev, _, _ in result.checks if sev == Severity.PASS) == passed
        assert sum(1 for _, sev, _, _ in result.checks if sev == Severity.WARN) == warnings


def test_substrate_386_proofs_verify_hash_signature():
    verifier = Substrate386PrimakoffVerifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_substrate_386_report_and_main(tmp_path):
    path = write_markdown_report(tmp_path / "substrate_386_primakoff_report.md")
    text = path.read_text(encoding="utf-8")

    assert "SUBSTRATO 386-PRIMAKOFF" in text
    assert "Phi_C: 0.928571" in text
    assert "axion beam is simulated" in text
    assert main()["substrate"] == "386-PRIMAKOFF"
