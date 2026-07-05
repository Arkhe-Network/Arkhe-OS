"""Tests for Substrate 955 — Safe-Core-PQC (Post-Quantum Processor)."""
import sys
sys.path.insert(0, "substrates/955-safe-core-pqc")
from safe_core_pqc import SafeCoreBridge


def test_attestation():
    bridge = SafeCoreBridge()
    att = bridge.get_attestation()
    assert att.device_id == "CORE-001"
    assert att.pubkey_kyber == "0xdeadbeef"
    assert len(att.seal) == 64


def test_pqc_instruction():
    bridge = SafeCoreBridge()
    result = bridge.execute_pqc_instruction("pqc.kem.encap", {"pk": "0x..."})
    assert result["status"] == "success"
    assert result["instruction"] == "pqc.kem.encap"


def test_secure_boot():
    bridge = SafeCoreBridge()
    result = bridge.secure_boot()
    assert result["status"] == "booted"
    assert bridge._booted


def test_generate_quote():
    bridge = SafeCoreBridge()
    quote = bridge.generate_quote("0xabcdef")
    assert "device_id" in quote
    assert "state_hash" in quote
    assert "seal" in quote
    assert len(quote["seal"]) == 64


def test_multiple_instructions():
    bridge = SafeCoreBridge()
    for instr in ["pqc.kem.encap", "pqc.sign.dilithium", "pqc.hash.sha3"]:
        bridge.execute_pqc_instruction(instr)
    assert bridge._instructions_executed == 3


def test_stats():
    bridge = SafeCoreBridge()
    stats = bridge.stats()
    assert stats["booted"] is False
    assert stats["instructions_executed"] == 0


def test_stats_after_boot():
    bridge = SafeCoreBridge()
    bridge.secure_boot()
    bridge.execute_pqc_instruction("pqc.sign.sphincs")
    stats = bridge.stats()
    assert stats["booted"] is True
    assert stats["instructions_executed"] == 1


def test_dilithium():
    bridge = SafeCoreBridge()
    result = bridge.execute_pqc_instruction("pqc.sign.dilithium", {"msg": "0x01"})
    assert result["status"] == "success"


def test_sphincs():
    bridge = SafeCoreBridge()
    result = bridge.execute_pqc_instruction("pqc.sign.sphincs", {"msg": "0x02"})
    assert result["status"] == "success"


def test_ntru():
    bridge = SafeCoreBridge()
    result = bridge.execute_pqc_instruction("pqc.ntru.encrypt", {"pt": "0x03"})
    assert result["status"] == "success"
