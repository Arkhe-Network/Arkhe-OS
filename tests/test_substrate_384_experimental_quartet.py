import hashlib
import math

from substrates.substrate_384.experimental_quartet import (
    AGITraining,
    ScoopPrototype,
    Severity,
    StrangeletSynthesis,
    Substrate384Verifier,
    WormholeObservation,
    main,
    write_markdown_report,
)


def _module(verifier, name):
    return next(result for result in verifier.results if result.module == name)


def test_scoop_prototype_matches_lab_scale_decree():
    scoop = ScoopPrototype()
    spec = scoop.get_spec()

    assert spec["scale"] == "1:1,000,000"
    assert spec["turns"] == 10
    assert math.isclose(scoop.compute_field_t() * 1000, 12.566370614359172, rel_tol=1e-12)
    assert spec["field_milli_tesla"] == 12.566
    assert spec["superconductor"] == "YBCO (HTS)"


def test_wormhole_observation_rounds_anomaly_candidates():
    obs = WormholeObservation().search_signatures()

    assert obs["telescopes"] == ["JWST", "Euclid", "Rubin", "Roman"]
    assert obs["survey_area_sq_deg"] == 15_000
    assert obs["halos_observed"] == 1_500
    assert obs["anomalous_halos"] == 5
    assert math.isclose(obs["anomalous_halos"] / obs["halos_observed"], 1 / 300)
    assert obs["confidence"] == 0.78


def test_agi_training_and_strangelet_models():
    train = AGITraining().train()
    synth = StrangeletSynthesis().simulate_collision()

    assert train["datasets"] == ["ADMX", "LUX-ZEPLIN", "XENON1T", "PandaX"]
    assert train["agents"] == 16
    assert train["accuracy_start"] == 0.65
    assert train["accuracy_end"] == 0.94
    assert train["false_positive_rate"] == 0.02
    assert train["improvement"] == "45%"
    assert synth["facilities"] == ["CERN-LHC", "FAIR-GSI", "RHIC-BNL", "NICA-JINR"]
    assert synth["energy_per_nucleon_gev"] == 100
    assert synth["strangelet_yield"] == 1e-8


def test_substrate_384_accounting_and_module_breakdown():
    verifier = Substrate384Verifier()
    verifier.run_verification()
    report = verifier.build_report()

    assert report.total_checks == 16
    assert report.passed_checks == 15
    assert report.warnings == 1
    assert report.phi_c == 0.9375

    for module in ["384-SCOOP-LAB", "384-WORMHOLE-OBS", "384-AGI-TRAIN"]:
        result = _module(verifier, module)
        assert len(result.checks) == 4
        assert all(sev == Severity.PASS for _, sev, _, _ in result.checks)

    strangelet = _module(verifier, "384-STRANGELET-SYNTH")
    assert len(strangelet.checks) == 4
    assert sum(1 for _, sev, _, _ in strangelet.checks if sev == Severity.WARN) == 1


def test_substrate_384_values_inside_checks():
    verifier = Substrate384Verifier()
    verifier.run_verification()

    scoop_field = next(det for inv, _, _, det in _module(verifier, "384-SCOOP-LAB").checks if inv == "SL2_FIELD")
    wormhole_anomaly = next(det for inv, _, _, det in _module(verifier, "384-WORMHOLE-OBS").checks if inv == "WO3_ANOMALIES")
    agi_fpr = next(det for inv, _, _, det in _module(verifier, "384-AGI-TRAIN").checks if inv == "AT3_FPR")
    strangelet_yield = next((sev, det) for inv, sev, _, det in _module(verifier, "384-STRANGELET-SYNTH").checks if inv == "SS4_YIELD")

    assert scoop_field["field_mT"] == 12.566
    assert scoop_field["expected_mT"] == 12.57
    assert wormhole_anomaly["anomalous"] == 5
    assert wormhole_anomaly["total"] == 1_500
    assert agi_fpr["fpr"] == 0.02
    assert strangelet_yield[0] == Severity.WARN
    assert strangelet_yield[1]["collisions_needed"] == 100_000_000


def test_substrate_384_proofs_verify_hash_signature():
    verifier = Substrate384Verifier()
    verifier.run_verification()

    for result in verifier.results:
        for proof in result.proofs:
            payload = (
                f"{proof.timestamp}|{proof.platform_hash}|{proof.module}|"
                f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
            )
            assert proof.signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_substrate_384_report_and_main(tmp_path):
    path = write_markdown_report(tmp_path / "substrate_384_experimental_quartet_report.md")
    text = path.read_text(encoding="utf-8")

    assert "SUBSTRATO 384" in text
    assert "Phi_C: 0.937500" in text
    assert "384-STRANGELET-SYNTH" in text
    assert main()["substrate"] == 384
