"""Tests for Substrate 355: Polycentric Governance."""
import sys
sys.path.insert(0, "substrates/substrate_355")
from polycentric_governance import PolycentricGovernance, create_default_gates, GHOST

import pytest


class TestPolycentricGovernance:
    def test_initialization(self):
        gov = PolycentricGovernance()
        assert gov.stats["total_gates"] == 0

    def test_register_gate(self):
        gov = PolycentricGovernance()
        g = gov.register_gate("TW-NA1", "North America")
        assert g.gate_id == "TW-NA1"
        assert g.region == "North America"
        assert gov.stats["total_gates"] == 1

    def test_register_gate_clamps_phi(self):
        gov = PolycentricGovernance()
        g = gov.register_gate("TW-TEST", "Test", phi_threshold=2.0)
        assert g.phi_threshold <= 0.9999

    def test_register_multiple_gates(self):
        gov = PolycentricGovernance()
        gov.register_gate("TW-NA1", "NA")
        gov.register_gate("TW-NA2", "NA")
        gov.register_gate("TW-EU1", "EU")
        assert gov.stats["total_gates"] == 3
        assert gov.stats["total_regions"] == 2

    def test_propose_rule_approved(self):
        gov = PolycentricGovernance()
        gov.register_gate("TW-NA1", "NA", peers=["TW-NA2", "TW-NA3"])
        gov.register_gate("TW-NA2", "NA", peers=["TW-NA1"])
        r = gov.propose_rule("TW-NA1", "rule_001", {"phi_threshold": GHOST * 1.1})
        assert r["status"] == "approved"

    def test_propose_rule_rejected_constitution(self):
        gov = PolycentricGovernance()
        gov.register_gate("TW-NA1", "NA")
        r = gov.propose_rule("TW-NA1", "bad_rule", {"phi_threshold": 0.0})
        assert r["status"] == "rejected"

    def test_propose_rule_nonexistent_gate(self):
        gov = PolycentricGovernance()
        r = gov.propose_rule("NONEXISTENT", "rule", {})
        assert r["status"] == "error"

    def test_create_default_gates(self):
        gov = create_default_gates()
        assert gov.stats["total_gates"] == 18  # 6 regions * 3 gates
        assert gov.stats["total_regions"] == 6

    def test_canonical_seal(self):
        gov = create_default_gates()
        seal = gov.canonical_seal()
        assert len(seal) == 64

    def test_region_tracking(self):
        gov = PolycentricGovernance()
        gov.register_gate("TW-SA1", "South America")
        assert "South America" in gov.regions
        assert "TW-SA1" in gov.regions["South America"]
