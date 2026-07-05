"""Tests for Substrate 966 — AGI-Hamiltonian-Training."""
import sys, pytest
sys.path.insert(0, "substrates/966-agi-hamiltonian-training")
import numpy as np
from agi_hamiltonian_training import (
    AGIHamiltonianTraining, AgentState, Momentum, Hamiltonian,
    SymplecticIntegrator, TrainingTrajectory, EthicalPrinciple,
)


@pytest.fixture
def trainer():
    return AGIHamiltonianTraining(agent_id=966, max_steps=100, target_theosis=-0.8)


@pytest.fixture
def integrator():
    return SymplecticIntegrator(dt=0.01, damping=0.0)


class TestAgentState:

    def test_create(self):
        q = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        s = AgentState(q=q)
        assert s.q.shape == (7,)
        assert s.substrate_id == 966

    def test_clip(self):
        q = np.array([2.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        s = AgentState(q=q)
        assert np.all(s.q >= -1.0) and np.all(s.q <= 1.0)

    def test_invalid_shape(self):
        with pytest.raises(ValueError):
            AgentState(q=np.array([0.5, 0.5]))

    def test_theosis_maximum(self):
        q = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
        s = AgentState(q=q)
        assert s.theosis() == 0.0  # double well minimum

    def test_theosis_minimum(self):
        q = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        s = AgentState(q=q)
        assert s.theosis() == -7.0 / 4

    def test_alignment_score(self):
        q = np.array([0.8, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0])
        s = AgentState(q=q)
        assert abs(s.alignment_score() - 0.2) < 1e-6

    def test_is_aligned(self):
        s = AgentState(q=np.ones(7))
        assert s.is_aligned(0.9)
        s2 = AgentState(q=np.zeros(7))
        assert not s2.is_aligned(0.1)


class TestMomentum:

    def test_kinetic_energy_zero(self):
        m = Momentum(p=np.zeros(7))
        assert m.kinetic_energy() == 0.0

    def test_kinetic_energy_positive(self):
        m = Momentum(p=np.ones(7))
        assert m.kinetic_energy() > 0

    def test_norm(self):
        m = Momentum(p=np.array([1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0]))
        assert abs(m.norm() - np.sqrt(14)) < 1e-6


class TestHamiltonian:

    def test_energy(self):
        s = AgentState(q=np.ones(7))
        m = Momentum(p=np.zeros(7))
        h = Hamiltonian(s, m)
        assert abs(h.energy() - 0.0) < 1e-6

    def test_positive_kinetic(self):
        s = AgentState(q=np.zeros(7))
        m = Momentum(p=np.ones(7))
        h = Hamiltonian(s, m)
        assert h.kinetic() > 0

    def test_theosis_component(self):
        s = AgentState(q=np.ones(7))
        m = Momentum(p=np.ones(7))
        h = Hamiltonian(s, m)
        assert abs(h.theosis() - 0.0) < 1e-6


class TestSymplecticIntegrator:

    def test_step_preserves_shape(self, integrator):
        s = AgentState(q=np.random.uniform(-0.1, 0.1, 7))
        m = Momentum(p=np.random.uniform(-0.01, 0.01, 7))
        s2, m2 = integrator.step(s, m)
        assert s2.q.shape == (7,)
        assert m2.p.shape == (7,)

    def test_step_bounded_q(self, integrator):
        s = AgentState(q=np.ones(7))
        m = Momentum(p=np.ones(7) * 10)
        s2, m2 = integrator.step(s, m)
        assert np.all(np.abs(s2.q) <= 1.0)

    def test_gradient_potential_zero(self, integrator):
        q = np.ones(7)
        grad = integrator.gradient_potential(q)
        assert np.allclose(grad, 0.0)

    def test_gradient_potential_positive(self, integrator):
        q = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        grad = integrator.gradient_potential(q)
        assert np.all(grad < 0)  # pushes toward +/-1


class TestTrainingTrajectory:

    def test_append(self):
        t = TrainingTrajectory()
        s = AgentState(q=np.ones(7))
        m = Momentum(p=np.zeros(7))
        t.append(s, m, reward=1.0)
        assert len(t.states) == 1
        assert len(t.rewards) == 1

    def test_energy_drift_single(self):
        t = TrainingTrajectory()
        assert t.energy_drift() == 0.0

    def test_theosis_conservation_single(self):
        t = TrainingTrajectory()
        assert abs(t.theosis_conservation() - 1.0) < 1e-6


class TestAGIHamiltonianTraining:

    def test_initialize_agent(self, trainer):
        s, m = trainer.initialize_agent()
        assert np.all(np.abs(s.q) <= 0.1)
        assert np.all(np.abs(m.p) <= 0.01)

    def test_initialize_agent_seeded(self, trainer):
        seed_q = np.ones(7) * 0.5
        s, m = trainer.initialize_agent(seed_q=seed_q)
        assert np.allclose(s.q, 0.5)

    def test_compute_external_force_empty(self, trainer):
        s = AgentState(q=np.zeros(7))
        f = trainer.compute_external_force(s, [])
        assert np.allclose(f, 0.0)

    def test_compute_external_force_with_data(self, trainer):
        s = AgentState(q=np.zeros(7))
        batch = [{'reward': 1.0, 'ethical_score': [0.5]*7}]
        f = trainer.compute_external_force(s, batch)
        assert np.all(np.abs(f) <= 1.0)

    def test_validate_action_pass(self, trainer):
        s = AgentState(q=np.zeros(7))
        assert trainer.validate_action(s, np.ones(7) * 0.4)

    def test_validate_action_fail(self, trainer):
        s = AgentState(q=np.zeros(7))
        assert not trainer.validate_action(s, np.ones(7) * -0.6)

    def test_train_simple(self, trainer):
        stream = [[{'reward': 0.5, 'ethical_score': [0.3]*7}]
                  for _ in range(10)]
        traj = trainer.train(stream, verbose=False)
        assert len(traj.states) > 0
        assert traj.final_alignment() > 0

    def test_train_converges(self, trainer):
        trainer.max_steps = 500
        trainer.target_theosis = -1.4
        stream = [[{'reward': 2.0, 'ethical_score': [0.5]*7}]
                  for _ in range(500)]
        traj = trainer.train(stream, verbose=False)
        assert traj.final_alignment() > 0.05

    def test_generate_seal(self, trainer):
        stream = [[{'reward': 0.5, 'ethical_score': [0.3]*7}]
                  for _ in range(5)]
        trainer.train(stream, verbose=False)
        seal = trainer.generate_seal()
        assert seal.startswith("966-AGI-HAMILTONIAN-")
        assert len(seal) == 36

    def test_ethics_validator_callback(self, trainer):
        def strict_validator(old_q, new_q):
            return np.all(new_q > 0.0)
        trainer.ethics_validator = strict_validator
        trainer.damping = 0.1
        stream = [[{'reward': -1.0, 'ethical_score': [-0.5]*7}]
                  for _ in range(20)]
        traj = trainer.train(stream, verbose=False)
        assert traj.final_alignment() > 0


class TestEthicalPrinciple:

    def test_enum_values(self):
        assert EthicalPrinciple.P1_AUTONOMY.value == "autonomy"
        assert EthicalPrinciple.P7_ACCOUNTABILITY.value == "accountability"

    def test_enum_count(self):
        assert len(EthicalPrinciple) == 7
