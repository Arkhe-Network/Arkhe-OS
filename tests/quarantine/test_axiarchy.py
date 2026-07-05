"""Tests for Substrate 954 — Axiarchy (Formal Ethics Kernel)."""
import sys
sys.path.insert(0, "substrates/954-axiarchy")
from axiarchy import AxiarchyVerifier, ALL_PRINCIPLES


def test_verify_valid():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "test-1"}, {}, {})
    assert proof.kernel_checked
    assert len(proof.principles_proved) == 7


def test_verify_multiple():
    av = AxiarchyVerifier()
    for i in range(5):
        proof = av.verify({"id": f"action-{i}"}, {}, {})
        assert proof.kernel_checked


def test_proof_has_seal():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "seal-me"}, {}, {})
    assert len(proof.seal) == 64


def test_proof_has_hash():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "hash-me"}, {}, {})
    assert len(proof.proof_hash) == 64


def test_all_principles_present():
    assert len(ALL_PRINCIPLES) == 7
    assert "P1" in ALL_PRINCIPLES
    assert "P7" in ALL_PRINCIPLES


def test_get_proof():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "find-me"}, {}, {})
    found = av.get_proof(proof.proof_id)
    assert found is not None
    assert found.proof_id == proof.proof_id


def test_get_proof_none():
    av = AxiarchyVerifier()
    assert av.get_proof("nonexistent") is None


def test_stats():
    av = AxiarchyVerifier()
    assert av.stats()["total_proofs"] == 0
    av.verify({"id": "a"}, {}, {})
    assert av.stats()["total_proofs"] == 1


def test_proof_id_format():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "fmt"}, {}, {})
    assert proof.proof_id.startswith("axiarchy-")


def test_proof_action_id():
    av = AxiarchyVerifier()
    proof = av.verify({"id": "custom-action"}, {}, {})
    assert proof.action_id == "custom-action"


def test_deterministic_hash():
    av = AxiarchyVerifier()
    p1 = av.verify({"id": "same"}, {}, {})
    # different proof_id each call but same action
    p2 = av.verify({"id": "same"}, {}, {})
    assert p1.proof_id != p2.proof_id
