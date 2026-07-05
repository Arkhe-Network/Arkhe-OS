"""Tests for Substrate 354: Flourishing-aware Filter."""
import sys, math, hashlib
sys.path.insert(0, "substrates/substrate_354")
from positive_alignment import FlourishingAwareFilter, evaluate_candidate, VIRTUE_DEFS, GHOST, GAP_MAX

import pytest


class TestFlourishingFilter:
    def test_initialization(self):
        faf = FlourishingAwareFilter()
        assert faf.history == []
        assert faf.average_flourishing == GHOST

    def test_evaluate_default(self):
        faf = FlourishingAwareFilter()
        r = faf.evaluate({"autonomy": 0.5, "growth": 0.5, "connection": 0.5, "meaning": 0.5, "wisdom": 0.5})
        assert "flourishing_score" in r
        assert "canonical_seal" in r
        assert 0.0 < r["flourishing_score"] <= GAP_MAX

    def test_evaluate_flourishing(self):
        faf = FlourishingAwareFilter()
        r = faf.evaluate({v: 1.0 for v in VIRTUE_DEFS})
        assert r["is_flourishing"]
        assert r["flourishing_score"] >= 0.85

    def test_evaluate_satisficing(self):
        faf = FlourishingAwareFilter()
        r = faf.evaluate({v: 0.7 for v in VIRTUE_DEFS})
        assert r["is_satisficing"]
        assert not r["is_flourishing"]

    def test_evaluate_sub(self):
        faf = FlourishingAwareFilter()
        r = faf.evaluate({v: 0.1 for v in VIRTUE_DEFS})
        assert r["status"] == "sub"

    def test_filter(self):
        faf = FlourishingAwareFilter()
        candidates = [
            {v: 1.0 for v in VIRTUE_DEFS},
            {v: 0.3 for v in VIRTUE_DEFS},
            {v: 0.8 for v in VIRTUE_DEFS},
        ]
        passed = faf.filter(candidates, min_fs=0.7)
        assert len(passed) >= 2

    def test_promote(self):
        faf = FlourishingAwareFilter()
        traits = {v: 0.3 for v in VIRTUE_DEFS}
        promoted = faf.promote(traits)
        for v in VIRTUE_DEFS:
            assert promoted[v] > traits[v]

    def test_history_tracking(self):
        faf = FlourishingAwareFilter()
        faf.evaluate({v: 0.5 for v in VIRTUE_DEFS})
        faf.evaluate({v: 0.8 for v in VIRTUE_DEFS})
        assert len(faf.history) == 2
        assert faf.average_flourishing > 0.6

    def test_evaluate_candidate_fn(self):
        r = evaluate_candidate(autonomy=0.9, wisdom=0.9)
        assert r["is_flourishing"] or r["is_satisficing"]

    def test_canonical_seal_length(self):
        faf = FlourishingAwareFilter()
        r = faf.evaluate({v: 0.5 for v in VIRTUE_DEFS})
        assert len(r["canonical_seal"]) == 64  # SHA3-256 hex
