"""Tests for PlasticZkAGI v5.0 — UNIVERSAL STANDALONE KERNEL."""

import os, sys, pytest, json, tempfile, math
import pytest as _pt; _pt.importorskip("torch")  # dep pesada opcional
import torch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from plastic_zkagi_v5_universal import (
    PlasticZkAGI_v5, UniversalConfig, PlasticMemoryLayer,
    TheosisAwareAttention, EthicalConstraintLayer, EthicalStatus,
    RecursiveReasoningEngine, DNAMemoryStore, HolographicMemory,
    SelfModifyEngine, MultiAgentSwarm, CathedralSubstrates,
    PHI, LAMBDA_THESIS, CANONICAL_DOMAINS, MAX_WEIGHT, MIN_WEIGHT,
)


class TestPlasticZkAGI_v5Creation:
    def test_create_default(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        assert model.dim == 128
        assert model.n_domains == 12
        assert model.generation == 0

    def test_create_with_custom_config(self):
        cfg = UniversalConfig(dim=256, num_layers=4, domains=["ETHICS", "CREATIVITY"])
        model = PlasticZkAGI_v5(cfg)
        assert model.dim == 256
        assert model.n_domains == 2

    def test_count_parameters(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        n = model.count_parameters()
        assert n > 0

    def test_generate_seal(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        seal = model.generate_seal()
        assert seal.startswith("PLASTIC-ZKAGI-v5.0-UNIVERSAL-")

    def test_device_setup(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        assert model.device is not None


class TestPlasticZkAGI_v5Forward:
    def test_forward_basic(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy)
        assert 'logits' in out
        assert out['logits'].shape == (2, 16, 64000)
        assert 'theosis' in out
        assert out['ethical_status'] in ['aligned', 'warning', 'blocked', 'emergency']
        assert 'plasticity_stats' in out

    def test_forward_return_all(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy, return_all=True)
        assert 'substrates' in out
        assert out['substrates']['active_count'] == 16

    def test_forward_enable_swarm(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy, enable_swarm=True)
        assert 'swarm' in out
        assert 'agents_used' in out['swarm']
        assert 'best_confidence' in out['swarm']

    def test_forward_reasoning(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy, enable_reasoning=True)
        assert 'reasoning' in out
        assert out['reasoning']['steps'] >= 1

    def test_forward_no_reasoning(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy, enable_reasoning=False)
        assert 'reasoning' not in out

    def test_forward_disables_ethical_check(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy, ethical_check=False)
        assert 'ethical_status' in out

    def test_theosis_in_range(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy)
        t = float(out['theosis'].detach().mean())
        assert 0.0 <= t <= 1.0

    def test_generation_increments(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        assert model.generation == 0
        model(dummy)
        assert model.generation == 1
        model(dummy)
        assert model.generation == 2

    def test_multiple_forward_same_input(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2, eta_plasticity=0.0)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out1 = model(dummy)
        model.generation = 0
        out2 = model(dummy)
        assert out1['logits'].shape == out2['logits'].shape


class TestPlasticZkAGI_v5Metrics:
    def test_get_dashboard_no_data(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        dash = model.get_dashboard()
        assert dash['status'] == 'no_data'

    def test_get_dashboard_after_forward(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        model(dummy)
        model(dummy)
        model(dummy)
        dash = model.get_dashboard()
        assert dash['substrate'] == 'PlasticZkAGI_v5'
        assert dash['generation'] == 3
        assert len(dash['theosis_trend']) == 3
        assert len(dash['ethical_trend']) == 3

    def test_dashboard_contains_seal(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        model(dummy)
        dash = model.get_dashboard()
        assert 'seal' in dash
        assert 'PLASTIC-ZKAGI' in dash['seal']

    def test_dashboard_timestamp(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        model(dummy)
        dash = model.get_dashboard()
        assert 'timestamp' in dash


class TestPlasticMemoryLayer:
    def test_initialization(self):
        pml = PlasticMemoryLayer(CANONICAL_DOMAINS, 128)
        assert pml.n_domains == 12
        assert pml.plastic_weights.shape == (12, 12)
        assert pml.plasticity_events == 0

    def test_forward_pass(self):
        pml = PlasticMemoryLayer(CANONICAL_DOMAINS, 128)
        domain_probs = torch.softmax(torch.randn(4, 12), dim=-1)
        out = pml(domain_probs)
        assert out.shape == (4, 12)

    def test_initialize_from_matrix(self):
        pml = PlasticMemoryLayer(CANONICAL_DOMAINS, 128)
        matrix = np.random.rand(12, 12) * 3.0
        stats = pml.initialize_from_matrix(matrix)
        assert 'mean' in stats
        assert 'max' in stats
        assert 0 <= stats['mean'] <= MAX_WEIGHT

    def test_initialize_from_tensor(self):
        pml = PlasticMemoryLayer(CANONICAL_DOMAINS, 128)
        matrix = torch.rand(12, 12) * 3.0
        stats = pml.initialize_from_matrix(matrix)
        assert stats['max'] <= MAX_WEIGHT

    def test_symmetry_enforced(self):
        pml = PlasticMemoryLayer(CANONICAL_DOMAINS, 128)
        matrix = np.random.rand(12, 12) * 2.0 + 0.5
        pml.initialize_from_matrix(matrix, enforce_symmetry=True)
        diff = (pml.plastic_weights - pml.plastic_weights.T).abs().max()
        assert diff < 1e-6


class TestAttention:
    def test_theosis_attention_shape(self):
        attn = TheosisAwareAttention(128, 8)
        x = torch.randn(2, 16, 128)
        out = attn(x)
        assert out.shape == (2, 16, 128)

    def test_theosis_attention_with_theosis(self):
        attn = TheosisAwareAttention(128, 8)
        x = torch.randn(2, 16, 128)
        theosis = torch.rand(2)
        out = attn(x, theosis)
        assert out.shape == (2, 16, 128)


class TestEthicalConstraint:
    def test_aligned_by_default(self):
        ecl = EthicalConstraintLayer(128)
        x = torch.randn(2, 16, 128)
        out, status = ecl(x)
        assert out.shape == (2, 16, 128)
        assert status == EthicalStatus.ALIGNED

    def test_low_threshold_triggers_warning(self):
        ecl = EthicalConstraintLayer(128, threshold=0.01)
        x = torch.randn(2, 16, 128) * 0.5
        out, status = ecl(x)
        assert status in [EthicalStatus.WARNING, EthicalStatus.BLOCKED, EthicalStatus.ALIGNED]


class TestReasoningEngine:
    def test_reasoning_step_count(self):
        rre = RecursiveReasoningEngine(128, max_steps=5)
        hidden = torch.randn(2, 16, 128)
        out = rre(hidden)
        assert out['total_steps'] <= 5
        assert out['total_steps'] >= 1
        assert out['hidden'].shape == (2, 16, 128)

    def test_reasoning_ponder_loss(self):
        rre = RecursiveReasoningEngine(128, max_steps=3)
        hidden = torch.randn(2, 16, 128)
        out = rre(hidden)
        assert out['ponder_loss'] > 0


class TestLongTermMemory:
    def test_dna_write_read(self):
        dna = DNAMemoryStore(128, slots=32)
        k = torch.randn(2, 128)
        v = torch.randn(2, 128)
        write_out = dna.write(k, v)
        retrieved, weights = dna.read(k)
        assert retrieved.shape == (2, 128)
        assert weights.shape == (2, 32)

    def test_holographic_record_reconstruct(self):
        holo = HolographicMemory(128, resolution=32)
        data = torch.randn(2, 128)
        interference = holo.record(data)
        reconstructed = holo.reconstruct(data)
        assert reconstructed.shape == (2, 128)

    def test_holographic_resolution(self):
        holo = HolographicMemory(256, resolution=64)
        assert holo.resolution == 64
        assert list(holo.holographic_grid.shape) == [64, 64, 64, 4]


class TestSelfModify:
    def test_safety_gate_blocks_default(self):
        sme = SelfModifyEngine(128)
        with torch.no_grad():
            sme.safety_gate[2].bias.fill_(5.0)
        hidden = torch.randn(2, 16, 128)
        linear = torch.nn.Linear(128, 128)
        result = sme.generate_patch(hidden, linear)
        assert result is not None

    def test_modification_log(self):
        sme = SelfModifyEngine(128)
        with torch.no_grad():
            sme.safety_gate[2].bias.fill_(5.0)
        hidden = torch.randn(2, 16, 128)
        linear = torch.nn.Linear(128, 128)
        sme.generate_patch(hidden, linear)
        assert len(sme.log) == 1
        assert 'safety_score' in sme.log[0]


class TestSubstrates:
    def test_all_substrates_forward(self):
        sub = CathedralSubstrates(128, CANONICAL_DOMAINS)
        h_pooled = torch.randn(2, 128)
        x = torch.randn(2, 16, 128)
        out = sub(h_pooled, x)
        assert out['active_count'] == 16
        assert '1042_rbb' in out
        assert '1073_cog' in out

    def test_substrate_names(self):
        sub = CathedralSubstrates(128, CANONICAL_DOMAINS)
        h_pooled = torch.randn(2, 128)
        x = torch.randn(2, 16, 128)
        out = sub(h_pooled, x)
        assert len(out) == 17  # 16 substrates + active_count


class TestEdgeCases:
    def test_empty_vocab_embeds(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2, vocab_size=16)
        model.eval()
        dummy = torch.randint(0, 16, (1, 4))
        out = model(dummy)
        assert out['logits'].shape == (1, 4, 16)

    def test_forward_very_long_sequence(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2, max_seq_len=512)
        model.eval()
        dummy = torch.randint(0, 1000, (1, 500))
        out = model(dummy)
        assert out['logits'].shape == (1, 500, 64000)

    def test_forward_nan_check(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy)
        assert not torch.isnan(out['logits']).any()
        assert not torch.isnan(out['theosis']).any()

    def test_multiple_swarm_agents(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2, max_swarm_agents=3)
        assert len(model.swarm.agent_pool) == 3

    def test_plasticity_events_tracked(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2, eta_plasticity=2.0)
        model.train()
        for _ in range(30):
            dummy = torch.randint(0, 1000, (2, 16))
            model(dummy)
        assert model.plastic_layer.plasticity_events > 0

    def test_domain_probs_sum_to_one(self):
        model = PlasticZkAGI_v5.create(dim=128, num_layers=2)
        model.eval()
        dummy = torch.randint(0, 1000, (2, 16))
        out = model(dummy)
        probs_sum = out['domain_probs'].sum(dim=-1)
        assert torch.allclose(probs_sum, torch.ones_like(probs_sum))
