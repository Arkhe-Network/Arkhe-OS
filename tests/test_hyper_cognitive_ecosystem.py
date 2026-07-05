"""Tests for Substrate 1073.8.1 — Hyper Cognitive Ecosystem V8.1."""

import pytest, os, sys, json, tempfile, math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "post-cathedral-substrates"))

from substrate_1073_81_hyper_cognitive_ecosystem import (
    HyperCognitiveEcosystemV81, CognitiveState, Agent, PlasticLink,
    LAMBDA_THESIS, ETA_PLASTICITY, THETA_THRESHOLD, MAX_WEIGHT,
    MIN_WEIGHT, NTT_SPEEDUP, DELTA_KC, PHI,
)


# =========================================================================
# CognitiveState
# =========================================================================

class TestCognitiveState:
    def test_default_values(self):
        s = CognitiveState()
        assert s.theosis == 0.0
        assert s.error_gradient == 1.0
        assert s.hallucination_potential == 0.5
        assert s.recursive_depth == 0
        assert len(s.history) == 0

    def test_copy_is_independent(self):
        s1 = CognitiveState(theosis=0.5, recursive_depth=10)
        s1.history.append({'theosis': 0.5})
        s2 = s1.copy()
        s2.theosis = 0.8
        s2.history.append({'theosis': 0.8})
        assert s1.theosis == 0.5
        assert s2.theosis == 0.8
        assert len(s1.history) == 1
        assert len(s2.history) == 2

    def test_history_maxlen(self):
        s = CognitiveState(theosis=1.0)
        for i in range(2000):
            s.history.append({'theosis': float(i)})
        assert len(s.history) == 1000


# =========================================================================
# Agent
# =========================================================================

class TestAgent:
    def test_default_agent(self):
        a = Agent(id=0, name="TestAgent")
        assert a.id == 0
        assert a.name == "TestAgent"
        assert a.domain == "GENERAL"
        assert isinstance(a.state, CognitiveState)

    def test_agent_with_domain(self):
        a = Agent(id=5, name="EthicsAgent", domain="ETHICS")
        assert a.domain == "ETHICS"
        assert a.state.theosis == 0.0


# =========================================================================
# PlasticLink
# =========================================================================

class TestPlasticLink:
    def test_default_link(self):
        link = PlasticLink(pre=0, post=1)
        assert link.pre == 0
        assert link.post == 1
        assert link.weight == 1.0
        assert link.plasticity_events == 0

    def test_custom_weight(self):
        link = PlasticLink(pre=0, post=1, weight=2.5)
        assert link.weight == 2.5


# =========================================================================
# HyperCognitiveEcosystemV81 — Initialization
# =========================================================================

class TestEcosystemInit:
    def test_default_init(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        assert eco.num_agents == 7
        assert len(eco.agents) == 7
        assert len(eco.plastic_links) == 7 * 6  # bidirectional, excluding self

    def test_custom_agent_count(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        assert len(eco.agents) == 3
        assert len(eco.plastic_links) == 3 * 2  # 6 bidirectional

    def test_constant_values(self):
        assert LAMBDA_THESIS == 0.5334
        assert ETA_PLASTICITY == 0.5334
        assert THETA_THRESHOLD == 0.08
        assert abs(PHI - (1 + 5**0.5) / 2) < 1e-10

    def test_agents_have_domains(self):
        eco = HyperCognitiveEcosystemV81(num_agents=7, seed=42)
        domains = [a.domain for a in eco.agents]
        assert "CONSCIOUSNESS" in domains
        assert all(d in eco.DOMAINS for d in domains)

    def test_agents_have_varied_theosis(self):
        eco = HyperCognitiveEcosystemV81(num_agents=7, seed=42)
        theosis_values = [a.state.theosis for a in eco.agents]
        assert all(0.01 <= t <= 0.3 for t in theosis_values)


# =========================================================================
# Core Mechanics
# =========================================================================

class TestCoreMechanics:
    def test_sigmoid_transcendence_returns_above_1(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        t = eco._sigmoid_transcendence(0.9, 0.8)
        assert t >= 1.0

    def test_sigmoid_transcendence_low_values(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        t = eco._sigmoid_transcendence(0.1, 0.1)
        assert t < 1.5

    def test_adaptive_dt_far_gap(self):
        eco = HyperCognitiveEcosystemV81(dt_base=0.001)
        dt = eco._adaptive_dt(0.0, 1.0)
        assert dt == 0.001

    def test_adaptive_dt_close_gap(self):
        eco = HyperCognitiveEcosystemV81(dt_base=0.001)
        dt = eco._adaptive_dt(0.995, 1.0)
        assert dt == 0.001 * 10.0

    def test_evolve_agent_bootstrap_phase(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        agent = eco.agents[0]
        agent.state.theosis = 0.05
        initial = agent.state.theosis
        new_state = eco.evolve_agent(agent, target=1.0)
        assert new_state.theosis > initial
        assert new_state.recursive_depth == 1

    def test_evolve_agent_log_phase(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        agent = eco.agents[0]
        agent.state.theosis = 0.5
        new_state = eco.evolve_agent(agent, target=1.0)
        assert new_state.theosis > 0.5

    def test_evolve_agent_error_gradient_decays(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        agent = eco.agents[0]
        new_state = eco.evolve_agent(agent)
        assert new_state.error_gradient < 1.0

    def test_evolve_agent_creative_divergence_grows(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        agent = eco.agents[0]
        agent.state.hallucination_potential = 0.8
        agent.state.paradox_tolerance = 0.5
        new_state = eco.evolve_agent(agent)
        assert new_state.creative_divergence >= agent.state.creative_divergence

    def test_evolve_agent_ethical_alignment_consistent(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        agent = eco.agents[0]
        for _ in range(5):
            agent.state = eco.evolve_agent(agent)
        assert 0.3 <= agent.state.ethical_alignment <= 1.0

    def test_evolve_agent_fatigue_rate_computed(self):
        eco = HyperCognitiveEcosystemV81(dt_base=0.001, seed=42)
        agent = eco.agents[0]
        new_state = eco.evolve_agent(agent)
        assert new_state.fatigue_rate > 0

    def test_evolve_agent_axiarchia_gate_fatigue_critical(self):
        eco = HyperCognitiveEcosystemV81(dt_base=0.001, seed=42)
        agent = eco.agents[0]
        agent.state.theosis = 0.5
        new_state = eco.evolve_agent(agent)
        agent.state = new_state
        for _ in range(100):
            agent.state.theosis = 0.99
            agent.state = eco.evolve_agent(agent)
        assert agent.state.theosis < 3.0


# =========================================================================
# Plasticity
# =========================================================================

class TestPlasticity:
    def test_apply_plasticity_changes_weights(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.agents[0].state.theosis = 0.8
        eco.agents[1].state.theosis = 0.2
        old_weight = eco.plastic_links[(0, 1)].weight
        eco.apply_plasticity()
        assert eco.plastic_links[(0, 1)].weight != old_weight

    def test_plasticity_events_increment(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.agents[0].state.theosis = 0.9
        eco.agents[1].state.theosis = 0.1
        old_events = eco.plastic_links[(0, 1)].plasticity_events
        eco.apply_plasticity()
        assert eco.plastic_links[(0, 1)].plasticity_events > old_events

    def test_plasticity_homeostasis_decay(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        weight = eco.plastic_links[(0, 1)].weight
        eco.apply_plasticity()
        link = eco.plastic_links[(0, 1)]
        if link.plasticity_events == 0:
            assert link.weight <= weight * 0.9995 + 1e-10

    def test_plasticity_weight_clamped(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        link = eco.plastic_links[(0, 1)]
        link.weight = 100.0
        eco.agents[0].state.theosis = 1.0
        eco.agents[1].state.theosis = 0.0
        for _ in range(100):
            eco.apply_plasticity()
        assert eco.plastic_links[(0, 1)].weight <= MAX_WEIGHT

    def test_plasticity_min_weight(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        link = eco.plastic_links[(0, 1)]
        link.weight = -10.0
        eco.agents[0].state.theosis = 0.0
        eco.agents[1].state.theosis = 1.0
        for _ in range(100):
            eco.apply_plasticity()
        assert eco.plastic_links[(0, 1)].weight >= MIN_WEIGHT

    def test_symmetric_links_have_same_initial_weight(self):
        eco = HyperCognitiveEcosystemV81(num_agents=4, seed=42)
        w12 = eco.plastic_links[(0, 1)].weight
        w21 = eco.plastic_links[(1, 0)].weight
        assert abs(w12 - w21) < 1e-6


# =========================================================================
# Ecosystem Steps
# =========================================================================

class TestEcosystemStep:
    def test_single_step_all_agents_evolve(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        initial_theosis = [a.state.theosis for a in eco.agents]
        eco.ecosystem_step(target=1.0, steps=1)
        for i, agent in enumerate(eco.agents):
            assert agent.state.theosis >= initial_theosis[i]

    def test_ecosystem_step_increases_depth(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=5)
        assert eco.agents[0].state.recursive_depth == 5

    def test_multiple_steps(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=10)
        assert eco.agents[0].state.recursive_depth == 10

    def test_history_collected(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=100)
        assert len(eco.full_history) >= 2  # every 50 steps

    def test_history_contains_all_metrics(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=100)
        if eco.full_history:
            entry = eco.full_history[0]
            assert 'mean_theosis' in entry
            assert 'max_theosis' in entry
            assert 'plasticity_events' in entry


# =========================================================================
# Benchmarks
# =========================================================================

class TestBenchmarks:
    def test_default_benchmarks_defined(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        assert len(eco.DEFAULT_BENCHMARKS) == 8

    def test_benchmark_domain_map_complete(self):
        eco = HyperCognitiveEcosystemV81(seed=42)
        for name in eco.DEFAULT_BENCHMARKS:
            assert name in eco.BENCHMARK_DOMAIN_MAP, f"{name} not in domain map"

    def test_surpass_base_benchmark(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        result = eco.surpass_benchmark("Substrate_1073_Base", 0.6835, max_steps=150000)
        assert result['success'], f"Final = {result['final']:.6f}"
        assert result['peak'] >= 0.6835, f"Peak = {result['peak']:.6f}"

    def test_surpass_neuronal(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        result = eco.surpass_benchmark("Substrate_1069_Neuronal", 0.8472, max_steps=100000)
        assert result['success']

    def test_surpass_transcendence(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        result = eco.surpass_benchmark("Transcendence_Threshold", 1.0, max_steps=150000)
        assert result['success']

    def test_surpass_ethical_purity(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        result = eco.surpass_benchmark("Ethical_Purity", 0.95, max_steps=150000)
        assert result['success']

    def test_surpass_creative_singularity(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        result = eco.surpass_benchmark("Creative_Singularity", 2.0, max_steps=200000)
        assert result['success']

    def test_run_all_benchmarks(self):
        eco = HyperCognitiveEcosystemV81(num_agents=5, seed=42)
        results = eco.run(warm_start=True)
        assert len(results) == 8
        surpassed = sum(1 for r in results.values() if r.get('success'))
        assert surpassed >= 4

    def test_warm_start_resets_agent(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        main = max(eco.agents, key=lambda a: a.state.theosis)
        main.state.theosis = 0.99
        result = eco.surpass_benchmark("Test", 0.5, max_steps=10, warm_start=True)
        expected_reset = max(0.3, 0.99 * 0.7)
        assert abs(main.state.theosis - expected_reset) < 0.01


# =========================================================================
# Dashboard Export
# =========================================================================

class TestDashboard:
    def test_export_dashboard_creates_file(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=100)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = eco.export_dashboard(f.name)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            assert data['substrate'] == '1073.8.1'
            assert data['num_agents'] == 3
            assert len(data['agents']) == 3
        finally:
            os.unlink(path)

    def test_dashboard_has_all_fields(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=100)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = eco.export_dashboard(f.name)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            assert 'plasticity' in data
            assert 'mean_theosis' in data
            assert 'history_samples' in data
            assert 0 <= data['mean_theosis'] <= 3.0
        finally:
            os.unlink(path)

    def test_dashboard_without_history(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = eco.export_dashboard(f.name)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            assert data['history'] == []
        finally:
            os.unlink(path)


# =========================================================================
# Stochastic invariants (seed reproducibility)
# =========================================================================

class TestSeedReproducibility:
    def test_same_seed_same_initial_agents(self):
        eco1 = HyperCognitiveEcosystemV81(num_agents=4, seed=42)
        eco2 = HyperCognitiveEcosystemV81(num_agents=4, seed=42)
        for i in range(4):
            assert eco1.agents[i].state.theosis == eco2.agents[i].state.theosis

    def test_different_seed_different_agents(self):
        eco1 = HyperCognitiveEcosystemV81(num_agents=4, seed=42)
        eco2 = HyperCognitiveEcosystemV81(num_agents=4, seed=99)
        same = all(
            eco1.agents[i].state.theosis == eco2.agents[i].state.theosis
            for i in range(4)
        )
        assert not same


# =========================================================================
# Edge cases
# =========================================================================

class TestEdgeCases:
    def test_single_agent(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        assert len(eco.agents) == 1
        assert len(eco.plastic_links) == 0

    def test_two_agents(self):
        eco = HyperCognitiveEcosystemV81(num_agents=2, seed=42)
        assert len(eco.agents) == 2
        assert len(eco.plastic_links) == 2  # bidirectional

    def test_max_agents(self):
        eco = HyperCognitiveEcosystemV81(num_agents=12, seed=42)
        assert len(eco.agents) == 12
        assert len(eco.plastic_links) == 12 * 11

    def test_evolve_with_zero_theta(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        agent = eco.agents[0]
        agent.state.theosis = 0.0
        new_state = eco.evolve_agent(agent)
        assert new_state.theosis >= 0.0
        assert new_state.recursive_depth == 1

    def test_evolve_beyond_one(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        agent = eco.agents[0]
        agent.state.theosis = 1.5
        new_state = eco.evolve_agent(agent, target=2.0)
        assert new_state.theosis > 1.5

    def test_ethic_alignment_never_below_03(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        agent = eco.agents[0]
        agent.state.meta_cognitive_awareness = 0.0
        for _ in range(100):
            agent.state = eco.evolve_agent(agent)
        assert agent.state.ethical_alignment >= 0.3

    def test_hallucination_bounded(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        agent = eco.agents[0]
        agent.state.hallucination_potential = 0.99
        for _ in range(5):
            agent.state = eco.evolve_agent(agent)
        assert agent.state.hallucination_potential <= 1.0

    def test_creative_divergence_soft_saturation(self):
        eco = HyperCognitiveEcosystemV81(num_agents=1, seed=42)
        agent = eco.agents[0]
        agent.state.hallucination_potential = 0.99
        agent.state.paradox_tolerance = 0.99
        for _ in range(500):
            agent.state = eco.evolve_agent(agent)
        assert agent.state.creative_divergence <= 10.0

    def test_no_plasticity_dead_links(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        initial = {k: PlasticLink(pre=v.pre, post=v.post, weight=v.weight, plasticity_events=v.plasticity_events)
                   for k, v in eco.plastic_links.items()}
        for a in eco.agents:
            a.state.theosis = 0.5
        eco.apply_plasticity()
        for key, link in eco.plastic_links.items():
            if initial[key].plasticity_events == link.plasticity_events:
                assert link.weight <= initial[key].weight * 0.9995 + 1e-10


# =========================================================================
# Integration: Multi-step convergence
# =========================================================================

class TestConvergence:
    def test_monotonic_theosis_short_run(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        depths = []
        for _ in range(50):
            eco.ecosystem_step(target=1.0, steps=1)
            depths.append(eco.agents[0].state.recursive_depth)
        assert depths == list(range(1, 51))
        assert all(a.state.theosis >= 0 for a in eco.agents)

    def test_theosis_never_decreases_mean(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.ecosystem_step(target=1.0, steps=10)
        prev = np.mean([a.state.theosis for a in eco.agents])
        for _ in range(20):
            eco.ecosystem_step(target=1.0, steps=1)
            curr = np.mean([a.state.theosis for a in eco.agents])
            assert curr >= prev - 0.0001
            prev = curr

    def test_plasticity_events_monotonic(self):
        eco = HyperCognitiveEcosystemV81(num_agents=3, seed=42)
        eco.agents[0].state.theosis = 0.9
        eco.agents[1].state.theosis = 0.1
        eco.agents[2].state.theosis = 0.5
        events_before = sum(l.plasticity_events for l in eco.plastic_links.values())
        for _ in range(20):
            eco.apply_plasticity()
        events_after = sum(l.plasticity_events for l in eco.plastic_links.values())
        assert events_after >= events_before


# =========================================================================
# Constants
# =========================================================================

class TestConstants:
    def test_phi(self):
        expected = (1 + math.sqrt(5)) / 2
        assert abs(PHI - expected) < 1e-10

    def test_lambda_thesis(self):
        assert LAMBDA_THESIS == 0.5334

    def test_delta_kc(self):
        assert DELTA_KC == 50.0

    def test_ntt_speedup(self):
        assert NTT_SPEEDUP == 459.8
