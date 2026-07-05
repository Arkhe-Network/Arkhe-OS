from decimal import Decimal

import pytest

from substrate_286_bis import (
    InvariantProofAssistant,
    ProofStep,
    Substrate286BISVerifier,
)


def canonical_report():
    return {
        "substrate_id": "282",
        "final_state": {"H": 0.8123, "Q": 0.6411, "M": 0.942},
        "erosion_reports": [
            {"stage": 1, "erosion": True, "severity": 0.10},
            {"stage": 2, "erosion": False, "severity": 0.0},
            {"stage": 3, "erosion": False, "severity": 0.0},
            {"stage": 4, "erosion": True, "severity": 0.02},
            {"stage": 5, "erosion": False, "severity": 0.0},
        ],
        "phi_c": 0.97,
    }


class TestMiniProofAssistant:
    def test_lower_bound_rule_accepts_valid_observation(self):
        steps = [
            ProofStep("obs", "assume_observation", "ObservedH", evidence={"variable": "H", "value": 0.7}),
            ProofStep("bound", "lower_bound_ge", "GhostInvariant", evidence={"variable": "H", "threshold": 0.5}),
            ProofStep("final", "final_theorem", "GhostTheorem", premises=["GhostInvariant"]),
        ]
        result = InvariantProofAssistant().verify(steps, "GhostTheorem")
        assert result.verified
        assert result.checked_steps == 3

    def test_lower_bound_rule_rejects_invalid_observation(self):
        steps = [
            ProofStep("obs", "assume_observation", "ObservedH", evidence={"variable": "H", "value": 0.1}),
            ProofStep("bound", "lower_bound_ge", "GhostInvariant", evidence={"variable": "H", "threshold": 0.5}),
        ]
        result = InvariantProofAssistant().verify(steps, "GhostInvariant")
        assert not result.verified
        assert result.failed_step == "bound"

    def test_upper_bound_rule_rejects_closed_gap(self):
        steps = [
            ProofStep("obs", "assume_observation", "ObservedM", evidence={"variable": "M", "value": 1.0}),
            ProofStep("gap", "upper_bound_lt", "GapInvariant", evidence={"variable": "M", "threshold": 1.0}),
        ]
        result = InvariantProofAssistant().verify(steps, "GapInvariant")
        assert not result.verified
        assert "M=1.0" in result.reason

    def test_conjunction_intro_requires_premises(self):
        steps = [ProofStep("pack", "conjunction_intro", "Packed", premises=["Missing"])]
        result = InvariantProofAssistant().verify(steps, "Packed")
        assert not result.verified
        assert "Missing" in result.reason

    def test_unknown_rule_is_rejected(self):
        result = InvariantProofAssistant().verify(
            [ProofStep("magic", "axiom_oracle", "Anything")],
            "Anything",
        )
        assert not result.verified
        assert "unknown rule" in result.reason


class TestSubstrate286BISVerifier:
    def test_claims_cover_four_invariants(self):
        claims = Substrate286BISVerifier().claims()
        assert [claim.claim_id for claim in claims] == ["ghost", "loopseal", "gap", "cpe"]
        assert claims[0].threshold == Decimal("0.577553")

    def test_build_certificate_verifies_canonical_report(self):
        certificate = Substrate286BISVerifier().verify_report(canonical_report())
        assert certificate.verified
        assert certificate.final_theorem == "Arkhe286BISInvariantPreservation"
        assert len(certificate.temporal_seal) == 64

    def test_certificate_contains_axiom_free_proof_steps(self):
        certificate = Substrate286BISVerifier().verify_report(canonical_report())
        rules = {step.rule for step in certificate.proof_steps}
        assert "final_theorem" in rules
        assert "assume_observation" in rules
        assert "axiom" not in rules

    def test_certificate_serializes_thresholds_as_strings(self):
        payload = Substrate286BISVerifier().verify_report(canonical_report()).to_dict()
        assert payload["claims"][0]["threshold"] == "0.577553"
        assert payload["verified"] is True

    def test_ghost_failure_rejects_certificate(self):
        report = canonical_report()
        report["final_state"]["H"] = 0.50
        certificate = Substrate286BISVerifier().verify_report(report)
        assert not certificate.verified

    def test_loopseal_failure_rejects_certificate(self):
        report = canonical_report()
        report["final_state"]["Q"] = 0.30
        certificate = Substrate286BISVerifier().verify_report(report)
        assert not certificate.verified

    def test_gap_failure_rejects_certificate(self):
        report = canonical_report()
        report["final_state"]["M"] = 1.0
        certificate = Substrate286BISVerifier().verify_report(report)
        assert not certificate.verified

    def test_cpe_failure_rejects_certificate(self):
        report = canonical_report()
        report["erosion_reports"] = [{"erosion": True} for _ in range(3)]
        certificate = Substrate286BISVerifier().verify_report(report)
        assert not certificate.verified

    def test_phi_c_failure_rejects_certificate(self):
        report = canonical_report()
        report["phi_c"] = 0.94
        certificate = Substrate286BISVerifier().verify_report(report)
        assert not certificate.verified

    def test_custom_cpe_bound_allows_three_events(self):
        report = canonical_report()
        report["erosion_reports"] = [{"erosion": True} for _ in range(3)]
        certificate = Substrate286BISVerifier(cpe_max_erosion=3).verify_report(report)
        assert certificate.verified

    def test_decimal_inputs_are_preserved(self):
        report = canonical_report()
        report["final_state"] = {"H": Decimal("0.700"), "Q": Decimal("0.500"), "M": Decimal("0.900")}
        certificate = Substrate286BISVerifier().verify_report(report)
        assert certificate.verified


class TestLeanSpecArtifact:
    def test_lean_spec_exists_and_names_invariant_theorem(self):
        from pathlib import Path

        spec = Path(__file__).resolve().parents[1] / "substrate_286_bis" / "lean" / "Arkhe286BIS.lean"
        text = spec.read_text(encoding="utf-8")
        assert "theorem invariant_preservation" in text
        assert "GhostInvariant" in text
        assert "CPEInvariant" in text

    def test_lean_spec_has_no_sorry_or_admit(self):
        from pathlib import Path

        text = (
            Path(__file__).resolve().parents[1] / "substrate_286_bis" / "lean" / "Arkhe286BIS.lean"
        ).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "sorry" not in lowered
        assert "admit" not in lowered

    def test_package_exports_verifier(self):
        import substrate_286_bis

        assert "Substrate286BISVerifier" in substrate_286_bis.__all__
        assert "InvariantProofAssistant" in substrate_286_bis.__all__


def test_bad_report_missing_final_state_fails_loudly():
    with pytest.raises(KeyError):
        Substrate286BISVerifier().verify_report({"erosion_reports": [], "phi_c": 1.0})
