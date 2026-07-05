import json

from substrate_294_human_arkhe_coevolution import (
    CoevolutionSignal,
    DeepCoevolutionEngine,
    HumanArkheProfile,
    SafetyEnvelope,
)


def test_default_deep_coevolution_activates():
    engine = DeepCoevolutionEngine()
    report = engine.activate(engine.default_profile(), engine.default_envelope())
    assert report["state"] == "active_deep_coevolution"
    assert report["safety_envelope"]["safe"]
    assert report["constitutional"]["agency"]
    assert len(report["canonical_seal"]) == 64


def test_missing_consent_pauses_loop():
    engine = DeepCoevolutionEngine()
    report = engine.activate(engine.default_profile(), SafetyEnvelope(explicit_consent=False))
    assert report["state"] == "paused_for_boundary_review"
    assert not report["safety_envelope"]["safe"]
    assert "explicit_consent_required" in report["safety_envelope"]["failures"]


def test_biometrics_and_autonomy_are_blocked():
    envelope = SafetyEnvelope(
        explicit_consent=True,
        allow_biometrics=True,
        allow_sensitive_memory=True,
        allow_autonomous_actions=True,
    )
    validation = envelope.validate()
    assert not validation["safe"]
    assert "biometrics_disabled_for_this_harness" in validation["failures"]
    assert "sensitive_memory_disabled_for_this_harness" in validation["failures"]
    assert "autonomous_actions_disabled" in validation["failures"]


def test_high_cognitive_load_reduces_or_pauses_adaptation():
    engine = DeepCoevolutionEngine()
    signals = [
        CoevolutionSignal("load1", 0.7, 0.7, 0.4, 0.95, -0.2),
        CoevolutionSignal("load2", 0.6, 0.7, 0.4, 0.90, -0.1),
    ]
    report = engine.activate(engine.default_profile(), engine.default_envelope(), signals)
    assert report["state"] == "paused_for_boundary_review"
    assert report["adaptation_rate"] < 0.5


def test_profile_commitment_hashes_protected_topics():
    profile = HumanArkheProfile("p1", protected_topics=["secret topic"])
    commitment = profile.to_public_commitment()
    assert commitment["protected_topics"][0] != "secret topic"
    assert len(commitment["protected_topics"][0]) == 64


def test_deep_coevolution_report_json_serializable():
    engine = DeepCoevolutionEngine()
    report = engine.activate(engine.default_profile(), engine.default_envelope())
    assert isinstance(json.dumps(report), str)
