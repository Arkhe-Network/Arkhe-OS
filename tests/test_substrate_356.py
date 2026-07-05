"""Tests for Substrate 356: Epistemic Humility Engine."""
import sys
sys.path.insert(0, "substrates/substrate_356")
from epistemic_humility import EpistemicHumilityEngine, evaluate_discovery, GHOST

import pytest


class TestEpistemicHumility:
    def test_initialization(self):
        ehe = EpistemicHumilityEngine()
        assert ehe.stats["count"] == 0

    def test_low_humility_discovery(self):
        ehe = EpistemicHumilityEngine()
        r = ehe.measure({"id": "low", "confidence": 0.99, "evidence": ["sim"]})
        assert r["level"] == "low"

    def test_high_humility_discovery(self):
        ehe = EpistemicHumilityEngine()
        r = ehe.measure({
            "id": "high", "confidence": 0.7,
            "evidence": ["sim", "theory", "exp", "peer"],
            "confidence_interval": (0.6, 0.8),
            "revision_plan": "Revisar após 6 meses",
            "limitations": ["Small sample", "Single lab"],
            "falsification_tests": ["Test A", "Test B"],
        })
        assert r["level"] == "high"
        assert r["humility"] > 0.5

    def test_moderate_humility(self):
        ehe = EpistemicHumilityEngine()
        r = ehe.measure({
            "id": "mod", "confidence": 0.6,
            "evidence": ["sim", "theory", "exp"],
            "confidence_interval": (0.4, 0.8),
            "limitations": ["one"],
            "falsification_tests": ["t1"],
        })
        assert r["level"] in ("moderate", "high")

    def test_preserve_already_high(self):
        ehe = EpistemicHumilityEngine()
        d = {
            "id": "p1", "confidence": 0.5,
            "evidence": ["sim", "exp"],
            "confidence_interval": (0.3, 0.7),
            "revision_plan": "revise",
            "limitations": ["low n"],
            "falsification_tests": ["t1"],
        }
        r = ehe.preserve(d, target=0.5)
        assert r["status"] == "preserved"

    def test_preserve_corrects(self):
        ehe = EpistemicHumilityEngine()
        d = {"id": "p2", "confidence": 0.99, "evidence": ["sim"]}
        r = ehe.preserve(d, target=0.8)
        assert r["status"] == "corrected"
        assert r["after"] > r["before"]

    def test_stats(self):
        ehe = EpistemicHumilityEngine()
        ehe.measure({"id": "s1", "confidence": 0.5, "evidence": ["e"]})
        ehe.measure({"id": "s2", "confidence": 0.7, "evidence": ["e"],
                     "confidence_interval": (0.1, 0.9), "revision_plan": "r",
                     "limitations": ["l"], "falsification_tests": ["f"]})
        s = ehe.stats
        assert s["count"] == 2
        assert s["mean"] > 0

    def test_recommendations(self):
        ehe = EpistemicHumilityEngine()
        r = ehe.measure({"id": "r1", "confidence": 0.99, "evidence": []})
        assert len(r["recommendations"]) > 0

    def test_canonical_seal(self):
        ehe = EpistemicHumilityEngine()
        assert len(ehe.canonical_seal()) == 64

    def test_evaluate_discovery_fn(self):
        r = evaluate_discovery(confidence=0.7, evidence_count=4, has_ci=True, has_revision=True,
                               limitations=["Small sample"])
        assert r["level"] in ("high", "moderate")

    def test_evaluate_discovery_low(self):
        r = evaluate_discovery(confidence=0.99, evidence_count=1)
        assert r["level"] == "low"
