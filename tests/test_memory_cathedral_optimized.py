"""Tests for Substrate 968 — Memory-Cathedral-Optimized."""
import sys, pytest
sys.path.insert(0, "substrates/968-memory-cathedral-optimized")
from memory_cathedral_optimized import MemoryCathedralOptimized, CacheAwareScheduler, PrefetchPlan, SchedulePolicy


class TestCacheAwareScheduler:
    def test_register_agent_l1(self):
        s = CacheAwareScheduler()
        assert s.register_agent(1, 32) == "L1d"

    def test_register_agent_l2(self):
        s = CacheAwareScheduler()
        assert s.register_agent(1, 256) == "L2"

    def test_register_agent_l3(self):
        s = CacheAwareScheduler()
        assert s.register_agent(1, 8192) == "L3"

    def test_register_agent_ram(self):
        s = CacheAwareScheduler()
        assert s.register_agent(1, 65536) == "RAM"

    def test_schedule_round_robin(self):
        s = CacheAwareScheduler()
        s.register_agent(1, 32); s.register_agent(2, 256)
        res = s.schedule(SchedulePolicy.ROUND_ROBIN)
        assert len(res) == 2


class TestMemoryCathedralOptimized:
    def test_analyze_working_set(self):
        mco = MemoryCathedralOptimized()
        r = mco.analyze_working_set(966, {"working_set_kb": 2048, "access_pattern": "sequential"})
        assert r["assigned_cache"] == "L3"
        assert r["substrate_id"] == 966

    def test_retrocausal_prefetch_single(self):
        mco = MemoryCathedralOptimized()
        p = mco.retrocausal_prefetch([100], depth=3)
        assert p.target_cache == "L3"
        assert p.priority == 0

    def test_retrocausal_prefetch_multi(self):
        mco = MemoryCathedralOptimized()
        p = mco.retrocausal_prefetch([100, 200, 300], depth=3)
        assert p.target_cache == "L2"
        assert p.priority == 1
        assert p.retrocausal_confidence > 0.5

    def test_generate_report(self):
        mco = MemoryCathedralOptimized()
        r = mco.generate_report([{"id": 966, "working_set_kb": 2048, "access_pattern": "sequential"}])
        assert "Substrato 968" in r
        assert "966" in r

    def test_schedule_policy_default(self):
        mco = MemoryCathedralOptimized()
        assert mco.schedule_policy == SchedulePolicy.CACHE_AWARE
