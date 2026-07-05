import hashlib
import math

from substrates.substrate_382 import (
    Advanced382Verifier,
    AxionMagneticScoop,
    FQTWormholeStabilityModel,
    HaloAGISensorMapper,
    StrangeletPropulsion,
)
from substrates.substrate_382.advanced_concepts import Severity, main


def test_axion_scoop_resonance_pressure_and_warning_boundary():
    scoop = AxionMagneticScoop()

    assert math.isclose(scoop.resonant_frequency_hz(), 24.17989242084918e9, rel_tol=1e-12)
    assert math.isclose(scoop.aperture_area_m2(), math.pi * 1e12, rel_tol=1e-12)
    assert scoop.magnetic_pressure_pa() > 5.0e7
    assert scoop.conversion_index() > 0


def test_fqt_wormhole_numeric_model_is_stable_but_speculative():
    model = FQTWormholeStabilityModel()

    assert model.flare_out_margin() > 1.0
    assert model.stability_score() > 0.9
    assert model.tidal_force_g() <= 3.0


def test_halo_sensor_mapper_fuses_multimodal_confidence():
    mapper = HaloAGISensorMapper()

    assert mapper.sensor_coverage() == 1.0
    assert 0.0 < mapper.fused_confidence() < 1.0
    assert 0.0 < mapper.halo_density_index() <= 1.0
    assert mapper.agi_agents == 16


def test_strangelet_propulsion_computes_power_and_flags_containment():
    model = StrangeletPropulsion()

    assert model.pulse_energy_j() == 9_600_000.0
    assert model.average_power_w() == 96_000_000.0
    assert model.photon_thrust_n() > 0.0
    assert model.acceleration_g() > 0.0
    assert model.containment_status() == "speculative-containment-required"


def test_advanced_verifier_accounting_has_four_warnings():
    verifier = Advanced382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 16
    assert report.passed_checks == 12
    assert report.warnings == 4
    assert report.phi_c == 0.75
    assert all(module["warn"] == 1 for module in report.modules.values())


def test_advanced_warning_boundaries_are_not_failures():
    verifier = Advanced382Verifier()
    verifier.run()

    for result in verifier.results:
        assert sum(1 for _, sev, _, _ in result.checks if sev == Severity.WARN) == 1
        assert all(sev != Severity.FAIL for _, sev, _, _ in result.checks)


def test_advanced_proofs_verify_hash_signature():
    verifier = Advanced382Verifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_advanced_main_returns_report():
    report = main()

    assert report["substrate"] == "382-advanced"
    assert report["status"] == "CANONIZED_SPECULATIVE_BRANCHES"
    assert report["total_checks"] == 16
