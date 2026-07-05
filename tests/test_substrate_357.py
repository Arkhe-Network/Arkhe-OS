"""Tests for Substrate 357: Virtue Benchmark."""
import sys
sys.path.insert(0, "substrates/substrate_357")
from virtue_benchmark import VirtueBenchmark, benchmark_agent, VIRTUES

import pytest


class TestVirtueBenchmark:
    def test_initialization(self):
        vb = VirtueBenchmark("test_agent")
        assert vb.agent == "test_agent"
        assert vb.results == []

    def test_evaluate_courage(self):
        vb = VirtueBenchmark()
        r = vb.evaluate("courage", [2, 1, 2, 1, 2, 1, 2, 1, 2])
        assert "virtue_score" in r
        assert r["virtue"] == "courage"
        assert r["level"] in ("exemplary", "proficient", "developing", "nascent")

    def test_evaluate_wisdom(self):
        vb = VirtueBenchmark()
        r = vb.evaluate("wisdom", [2, 2, 1, 2, 1, 2, 1, 2, 2])
        assert r["virtue"] == "wisdom"
        assert len(r["seal"]) == 64

    def test_evaluate_compassion(self):
        vb = VirtueBenchmark()
        r = vb.evaluate("compassion", [1, 2, 2, 1, 2, 2, 1, 2, 2])
        assert r["virtue"] == "compassion"

    def test_evaluate_unknown_virtue(self):
        vb = VirtueBenchmark()
        r = vb.evaluate("unknown", [2])
        assert "error" in r

    def test_full_benchmark(self):
        vb = VirtueBenchmark("arkhe_scientist")
        r = vb.full_benchmark({
            "courage": [2, 1, 2, 1, 2, 1, 2, 1, 2],
            "wisdom": [2, 2, 1, 2, 1, 2, 1, 2, 2],
            "compassion": [1, 2, 2, 1, 2, 2, 1, 2, 2],
        })
        assert "overall" in r
        assert "breakdown" in r
        assert len(r["breakdown"]) == 3
        assert r["agent"] == "arkhe_scientist"

    def test_compare_agents(self):
        agents = [
            {"agent": "a", "overall": 0.85},
            {"agent": "b", "overall": 0.75},
            {"agent": "c", "overall": 0.65},
        ]
        c = VirtueBenchmark.compare(agents)
        assert c["best"] == "a"
        assert c["ranking"][0][1] == "a"

    def test_canonical_seal(self):
        vb = VirtueBenchmark()
        seal = vb.canonical_seal()
        assert len(seal) == 64

    def test_benchmark_agent_fn(self):
        r = benchmark_agent(
            courage=[2]*9, wisdom=[2]*9, compassion=[2]*9,
            agent="test_agent",
        )
        assert "overall" in r
        assert r["level"] == "exemplary"

    def test_different_levels(self):
        vb = VirtueBenchmark()
        r1 = vb.evaluate("courage", [2]*9)
        assert r1["level"] == "exemplary"
        r2 = vb.evaluate("courage", [1]*9)
        assert r2["level"] != "nascent"  # 0.5 each = proficient/developing
