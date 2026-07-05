"""Tests for Substrate 971 — Self-Reflexive-Cathedral."""
import sys, pytest
sys.path.insert(0, "substrates/971-self-reflexive-cathedral")
from self_reflexive_cathedral import SelfReflexiveCathedral


@pytest.fixture
def meta():
    m = SelfReflexiveCathedral()
    substrates_data = [
        (966, "AGI-Hamiltonian-Training", 19751, [965, 951, 952, 953, 954, 266, 268, 890, 248], [965, 951]),
        (967, "Memory-Hierarchy-Cathedral", 19672, [965, 960, 955, 276, 260, 266, 268], [960]),
        (965, "Hamiltonian-Cathedral", 0, [960, 961, 962, 248, 1, 963], [960]),
        (960, "ARKHE-STACK", 0, [955, 276, 260, 266, 268, 890, 923, 933], [955, 276]),
        (951, "Conscious-Replay", 0, [266, 268, 276, 277, 278, 890, 924, 933, 934, 295, 563, 608], [266, 890]),
        (952, "Bindu", 0, [266, 268, 276, 277, 278, 890, 924, 933, 934, 295, 563, 608, 951], [951]),
        (953, "Tanmatra", 0, [951, 952, 954, 608, 563, 568, 890, 934, 554, 947, 955], [951, 952, 954]),
        (954, "Axiarchy", 0, [951, 952, 953, 955, 957, 958, 960, 963, 964, 965], [951, 952, 953]),
        (890, "World-Model-V3", 0, [266, 268, 276, 890, 924, 933, 934, 295, 563, 608], [266]),
        (923, "TemporalChain", 0, [255, 260, 261, 933, 262, 930, 912], [255, 260]),
        (933, "FluxMem", 0, [912, 913, 262, 255], [912, 913]),
        (248, "Retrocausal-Caching", 0, [1, 900, 960, 965], [1, 900]),
    ]
    for sid, name, size, links, deps in substrates_data:
        m.register_substrate(sid, name, size, links, deps)
    return m


class TestSelfReflexiveCathedral:
    def test_register_substrate(self):
        m = SelfReflexiveCathedral()
        m.register_substrate(1, "test", 100, [2, 3], [])
        assert 1 in m.substrates

    def test_build_dependency_graph(self, meta):
        meta.build_dependency_graph()
        assert len(meta.substrates[951].dependents) > 0

    def test_compute_entropy(self, meta):
        meta.compute_entropy()
        for comp in meta.substrates.values():
            assert 0.0 <= comp.entropy <= 1.0

    def test_compute_theosis(self, meta):
        meta.compute_theosis_contribution()
        for comp in meta.substrates.values():
            assert comp.theosis_contribution >= 0.0

    def test_compute_circularity(self, meta):
        c = meta.compute_circularity()
        assert 0.0 <= c <= 1.0

    def test_compute_resilience(self, meta):
        r = meta.compute_resilience()
        assert 0.0 <= r <= 1.0

    def test_find_bottlenecks(self, meta):
        b = meta.find_bottlenecks()
        assert isinstance(b, list)

    def test_find_orphans(self, meta):
        o = meta.find_orphans()
        assert isinstance(o, list)

    def test_find_clusters(self, meta):
        c = meta.find_clusters()
        assert len(c) >= 1
        all_ids = []
        for cluster in c:
            all_ids.extend(cluster)
        assert len(set(all_ids)) == len(meta.substrates)

    def test_analyze(self, meta):
        a = meta.analyze()
        assert a.total_substrates == 12
        assert a.seal.startswith("971-SELF-REFLEXIVE-")
        assert len(a.seal) == 35

    def test_generate_report(self, meta):
        meta.analyze()
        r = meta.generate_report()
        assert "SUBSTRATO 971" in r
        assert meta.meta_analysis.seal in r
