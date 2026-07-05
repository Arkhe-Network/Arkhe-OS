import hashlib
import json

from substrates.substrate_228 import (
    Arkhe228Verifier,
    OctraDocsSnapshot,
    Severity,
    create_failing_program,
    create_private_ml_program,
    create_token_program,
    run_test_suite,
)


def test_official_docs_snapshot_contains_only_verified_core_facts():
    docs = OctraDocsSnapshot()

    assert docs.founded_year == 2021
    assert docs.internal_prototype == "October 2023"
    assert docs.public_testnet == "June 2025"
    assert docs.mainnet_alpha == "December 2025"
    assert docs.node_types == ("bootstrap", "standard", "light")
    assert docs.hfhe_gates == ("AND", "OR", "XOR", "NOT", "NAND", "NOR", "XNOR")
    assert "market_cap" not in docs.__dict__
    assert "public_sale" not in docs.__dict__


def test_token_program_passes_with_visible_lowering_and_interface():
    report = Arkhe228Verifier(create_token_program()).run_full_verification()

    assert report["audit"]["constitutional_compliance"] is True
    assert report["action"]["decision"] == "DEPLOY"
    assert report["audit"]["failures"] == 0


def test_private_ml_program_exercises_hfhe_path_without_failures():
    report = Arkhe228Verifier(create_private_ml_program()).run_full_verification()
    checks = [check for result in report["results"] for check in result.invariant_checks]

    assert report["audit"]["constitutional_compliance"] is True
    assert any(inv.value == "C1" and sev == Severity.PASS for inv, sev, _, _ in checks)
    assert any(inv.value == "L7" and sev == Severity.PASS for inv, sev, _, _ in checks)


def test_failing_program_is_rejected_for_hidden_lowering():
    report = Arkhe228Verifier(create_failing_program()).run_full_verification()
    checks = [check for result in report["results"] for check in result.invariant_checks]

    assert report["audit"]["constitutional_compliance"] is False
    assert report["action"]["decision"] == "CORRIGIR"
    assert any(inv.value == "L1" and sev == Severity.FAIL for inv, sev, _, _ in checks)
    assert any(inv.value == "L2" and sev == Severity.FAIL for inv, sev, _, _ in checks)


def test_proof_packets_are_hash_bound():
    report = Arkhe228Verifier(create_token_program()).run_full_verification()

    for proof in report["proofs"]:
        payload = (
            f"{proof.timestamp}|{proof.design_hash}|{proof.module_name}|"
            f"{proof.invariant}|{proof.severity}|{proof.message}|{proof.details}"
        )
        assert proof.verifier_signature == hashlib.sha3_256(payload.encode()).hexdigest()[:32]


def test_suite_summary_is_json_serializable_and_sealed():
    summary = run_test_suite()
    compact = {k: v for k, v in summary.items() if k != "reports"}

    assert summary["total_tests"] == 6
    assert summary["passed_tests"] == 6
    assert len(summary["seal"]) == 64
    assert summary["proofs_verified"] == 42
    json.dumps(compact)
