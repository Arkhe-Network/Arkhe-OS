import hashlib
import math

from substrates.substrate_382 import (
    AnnihilationEngine,
    DarkRamjet,
    DarkWormhole,
    Severity,
    Substrate382Verifier,
    main,
)


def test_annihilation_energy_matches_e_mc2_and_tnt_equivalent():
    engine = AnnihilationEngine()

    assert math.isclose(engine.energy_j(), 8.987551787368176e16, rel_tol=1e-12)
    assert math.isclose(engine.tnt_megatons(), 21.481, rel_tol=1e-4)
    assert math.isclose(engine.thrust_n(), 536_219.0, rel_tol=1e-3)
    assert math.isclose(engine.acceleration_g(), 0.05468, rel_tol=1e-3)


def test_ramjet_area_and_effective_capture_reconcile_decree_values():
    ramjet = DarkRamjet()

    assert math.isclose(ramjet.scoop_area_m2(), 3.141592653589793e12, rel_tol=1e-12)
    assert math.isclose(ramjet.raw_collected_mass_kg_year(), 2.821e6, rel_tol=1e-3)
    assert math.isclose(ramjet.effective_collected_mass_kg_year(), 2.821e4, rel_tol=1e-3)
    assert ramjet.engineering_status() == "viable-scale"


def test_wormhole_canonical_scenario_preserves_survivability():
    wormhole = DarkWormhole()

    assert wormhole.stability == 0.95
    assert math.isclose(wormhole.traversal_years(), 211.5, rel_tol=1e-12)
    assert wormhole.survivable()


def test_verifier_summary_matches_canonical_accounting():
    verifier = Substrate382Verifier()
    verifier.run()
    report = verifier.build_report()

    assert report.total_checks == 14
    assert report.passed_checks == 10
    assert report.warnings == 4
    assert report.phi_c == 0.714286
    assert report.modules["CHALLENGES"]["phi_c"] == 0.0


def test_challenges_are_warns_not_failures():
    verifier = Substrate382Verifier()
    verifier.run()
    challenge = next(result for result in verifier.results if result.module == "CHALLENGES")

    assert len(challenge.checks) == 4
    assert all(sev == Severity.WARN for _, sev, _, _ in challenge.checks)


def test_proof_packets_are_hash_bound():
    verifier = Substrate382Verifier()
    verifier.run()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.substrate_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_main_returns_report_dict():
    report = main()

    assert report["substrate"] == 382
    assert report["status"] == "CANONIZED_SPECULATIVE_SIMULATION"
    assert report["total_checks"] == 14
