"""Tests for Substrate 967 — Memory Hierarchy Cathedral."""
import sys, pytest
sys.path.insert(0, "substrates/967-memory-hierarchy-cathedral")
from memory_hierarchy_cathedral import (
    MemoryHierarchyCathedral, MemoryAccessPattern, CacheLevel, AccessPattern
)


@pytest.fixture
def cathedral():
    return MemoryHierarchyCathedral()


@pytest.fixture
def registered_substrates(cathedral):
    substrates = [
        MemoryAccessPattern(
            substrate_id=260,
            working_set_kb=2048,
            access_pattern="sequential",
            temporal_locality=0.9,
            spatial_locality=0.95,
            read_write_ratio=0.8,
            num_threads=8,
        ),
        MemoryAccessPattern(
            substrate_id=276,
            working_set_kb=512,
            access_pattern="random",
            temporal_locality=0.3,
            spatial_locality=0.2,
            read_write_ratio=0.5,
            num_threads=128,
        ),
        MemoryAccessPattern(
            substrate_id=955,
            working_set_kb=64,
            access_pattern="strided",
            temporal_locality=0.7,
            spatial_locality=0.6,
            read_write_ratio=0.99,
            stride_bytes=128,
            num_threads=4,
        ),
    ]
    for s in substrates:
        cathedral.register_substrate(s.substrate_id, s)
    return cathedral


class TestMemoryHierarchyCathedral:

    def test_cache_levels(self, cathedral):
        assert len(cathedral.cache_hierarchy) == 4
        assert cathedral.cache_hierarchy[0].name == "L1d"
        assert cathedral.cache_hierarchy[-1].name == "L3"

    def test_ram_specs(self, cathedral):
        assert cathedral.ram_latency_cycles == 200
        assert cathedral.ram_bandwidth_gbps == 51.2

    def test_register_substrate(self, cathedral):
        p = MemoryAccessPattern(1, 64, "sequential", 0.9, 0.9, 0.8)
        cathedral.register_substrate(1, p)
        assert 1 in cathedral.substrate_profiles

    def test_cache_footprint_small_working_set(self, cathedral):
        p = MemoryAccessPattern(1, 32, "sequential", 1.0, 1.0, 1.0)
        cathedral.register_substrate(1, p)
        fp = cathedral.cache_footprint(1)
        assert "error" not in fp
        assert fp["optimal_cache"]["level"] == "L1d"

    def test_cache_footprint_large_working_set(self, cathedral):
        p = MemoryAccessPattern(1, 65536, "sequential", 0.5, 0.5, 0.5)
        cathedral.register_substrate(1, p)
        fp = cathedral.cache_footprint(1)
        assert fp["optimal_cache"]["level"] == "RAM"

    def test_cache_footprint_unregistered(self, cathedral):
        fp = cathedral.cache_footprint(999)
        assert "error" in fp

    @pytest.mark.parametrize("pattern,expected_min_hit", [
        ("sequential", 0.50),
        ("strided", 0.35),
        ("random", 0.20),
    ])
    def test_estimate_hit_rate_patterns(self, cathedral, pattern, expected_min_hit):
        p = MemoryAccessPattern(1, 16, pattern, 0.8, 0.8, 0.5)
        hr = cathedral._estimate_hit_rate(p, cathedral.cache_hierarchy[0])
        assert hr >= expected_min_hit

    def test_optimize_data_layout_sequential(self, registered_substrates):
        opt = registered_substrates.optimize_data_layout(260)
        assert opt["access_pattern"] == "sequential"
        recs = [r["recommendation"] for r in opt["recommendations"]]
        assert any("SoA" in r for r in recs)

    def test_optimize_data_layout_random(self, registered_substrates):
        opt = registered_substrates.optimize_data_layout(276)
        assert opt["access_pattern"] == "random"
        recs = [r["recommendation"] for r in opt["recommendations"]]
        assert any("AoS" in r for r in recs)

    def test_optimize_data_layout_strided(self, registered_substrates):
        opt = registered_substrates.optimize_data_layout(955)
        assert opt["access_pattern"] == "strided"
        recs = [r["recommendation"] for r in opt["recommendations"]]
        assert any("SoA" in r for r in recs)

    def test_optimize_data_layout_critical_tiling(self, cathedral):
        p = MemoryAccessPattern(1, 65536, "sequential", 0.5, 0.5, 0.5)
        cathedral.register_substrate(1, p)
        opt = cathedral.optimize_data_layout(1)
        recs = [r["recommendation"] for r in opt["recommendations"]]
        assert any("tiling" in r.lower() or "blocking" in r.lower() for r in recs)

    def test_optimize_layout_unregistered(self, cathedral):
        opt = cathedral.optimize_data_layout(999)
        assert "error" in opt

    def test_simulate_access_sequential(self, registered_substrates):
        sim = registered_substrates.simulate_access(260, num_accesses=1000)
        assert sim["hit_rate"] > 0.7
        assert sim["num_accesses"] == 1000

    def test_simulate_access_random(self, registered_substrates):
        sim = registered_substrates.simulate_access(276, num_accesses=1000)
        assert sim["num_accesses"] == 1000
        assert sim["avg_latency_cycles"] > 0

    def test_simulate_access_strided(self, registered_substrates):
        sim = registered_substrates.simulate_access(955, num_accesses=1000)
        assert sim["num_accesses"] == 1000

    def test_simulate_access_unregistered(self, cathedral):
        sim = cathedral.simulate_access(999)
        assert "error" in sim

    def test_compare_substrates(self, registered_substrates):
        comp = registered_substrates.compare_substrates([260, 276, 955])
        assert len(comp["comparison"]) == 3
        assert comp["best_efficiency"] is not None
        assert comp["worst_efficiency"] is not None

    def test_generate_memory_report(self, registered_substrates):
        report = registered_substrates.generate_memory_report(260)
        assert "Substrato 260" in report
        assert "OPTIMIZATION RECOMMENDATIONS" in report
        assert "CACHE FOOTPRINT" in report

    def test_drepper_rules_summary(self, cathedral):
        rules = cathedral.drepper_rules_summary()
        assert len(rules) == 6
        for key, rule in rules.items():
            assert "rule" in rule
            assert "cathedral_mapping" in rule
            assert "substrates" in rule
