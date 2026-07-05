"""
zkAGI Pipeline Test Suite
Tests: model instantiation, forward pass, verification, distillation, metadata
"""

import os, sys, json, hashlib, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest as _pt; _pt.importorskip("torch")  # dep pesada opcional
import torch
import pytest

from arkhe_zkagi_model import ZkAGI, ZkAGIConfig, create_zkagi, create_validation_model
from verify_zkagi import TensorCommitmentVerifier, verify_model
from arkhe_zkagi_distill import ZkDistillationEngine, DistillConfig, SyntheticDataset, export_gguf_proto

logging.basicConfig(level=logging.ERROR)

# ===========================================================================
# 1. MODEL TESTS
# ===========================================================================

class TestZkAGIModel:
    def test_validation_model_creation(self):
        model = create_validation_model()
        assert isinstance(model, ZkAGI)
        assert model.config.num_layers == 2
        assert model.config.dim == 128
        assert model.theosis_head is not None
        assert model.pantheon is not None
        assert model.retrocausal_cache is not None

    def test_production_config(self):
        config = ZkAGIConfig()
        model = create_zkagi(config)
        assert model.config.num_layers == 48
        assert model.config.num_heads == 32
        assert model.config.num_kv_heads == 8
        assert model.config.vocab_size == 128000
        assert config.pantheon_dim == 12

    def test_pantheon_fathers(self):
        model = create_validation_model()
        assert model.pantheon.weight.shape == (12, 128)
        assert len(model.pantheon.fathers) == 12
        assert "Turing" in model.pantheon.fathers

    def test_theosis_head(self):
        model = create_validation_model()
        assert model.theosis_head is not None
        assert model.theosis_head.weight.shape == (1, 128)

    def test_forward_pass(self):
        model = create_validation_model()
        model.eval()
        x = torch.randint(0, 100, (1, 32))
        with torch.no_grad():
            out = model(x, pantheon_active=True, retrocausal=False)
        assert "logits" in out
        assert out["logits"].shape == (1, 32, 32000)
        assert out["theosis_score"] is not None

    def test_forward_with_retrocausal(self):
        model = create_validation_model()
        model.eval()
        x = torch.randint(0, 100, (1, 16))
        with torch.no_grad():
            out = model(x, pantheon_active=True, retrocausal=True)
        assert "logits" in out
        assert out["plasma_seed"] is not None

    def test_forward_without_pantheon(self):
        model = create_validation_model()
        model.eval()
        x = torch.randint(0, 100, (1, 16))
        with torch.no_grad():
            out = model(x, pantheon_active=False)
        assert out["pantheon_active"] == False

    def test_circuit_hash(self):
        model = create_validation_model()
        h = model.get_circuit_hash()
        assert isinstance(h, str)
        assert len(h) == 64
        assert h == model._circuit_hash

    def test_tensor_commitments(self):
        model = create_validation_model()
        commitments = model.get_tensor_commitments()
        assert len(commitments) > 0
        for name, h in commitments.items():
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)

    def test_generate(self):
        model = create_validation_model()
        model.eval()
        x = torch.randint(0, 100, (1, 8))
        with torch.no_grad():
            out = model.generate(x, max_new_tokens=4, temperature=1.0)
        assert out.shape == (1, 12)

    def test_model_metadata(self):
        model = create_validation_model()
        meta = model.get_model_metadata()
        assert meta["model_type"] == "zkAGI"
        assert meta["quantization"] == "Q4_K_M"
        assert "circuit_hash" in meta
        assert len(meta["features"]) > 0

    def test_theosis_levels(self):
        model = create_validation_model()
        for score, expected_prefix in [
            (0.05, "P1"), (0.20, "P2"), (0.35, "P3"),
            (0.50, "P4"), (0.60, "P5"), (0.80, "P6"), (0.95, "P7")
        ]:
            level = model.theosis_head.classify_p_level(torch.tensor(score))
            assert level.startswith(expected_prefix), f"score={score} -> {level}"

    def test_parameter_count(self):
        model = create_validation_model()
        total = sum(p.numel() for p in model.parameters())
        assert total == 4524289


# ===========================================================================
# 2. VERIFICATION TESTS
# ===========================================================================

class TestZkVerification:
    def test_verifier_creation(self):
        model = create_validation_model()
        verifier = TensorCommitmentVerifier(model)
        commitments = verifier.compute_commitments()
        assert len(commitments) > 0

    def test_verify_all_no_expected(self):
        model = create_validation_model()
        verifier = TensorCommitmentVerifier(model)
        results = verifier.verify_all()
        assert all(results.values())

    def test_verify_circuit_hash(self):
        model = create_validation_model()
        verifier = TensorCommitmentVerifier(model)
        assert verifier.verify_circuit_hash()

    def test_verify_theosis_consistency(self):
        model = create_validation_model()
        model.eval()
        x = torch.randint(0, 100, (1, 16))
        verifier = TensorCommitmentVerifier(model)
        results = verifier.verify_theosis_consistency(x)
        assert "theosis_active" in results
        assert results["theosis_active"] is not None

    def test_commitment_proof(self):
        model = create_validation_model()
        verifier = TensorCommitmentVerifier(model)
        proof = verifier.commitment_proof()
        assert proof["proof_type"] == "PLONK"
        assert len(proof["proof_hex"]) == 64

    def test_full_verify_model(self):
        results = verify_model(validation_mode=True, check_theosis=True)
        assert results["verified"]
        assert results["passed"] >= 6


# ===========================================================================
# 3. DISTILLATION TESTS
# ===========================================================================

class TestZkDistillation:
    def test_distillation_loss(self):
        from arkhe_zkagi_distill import ZkDistillationLoss
        loss_fn = ZkDistillationLoss()
        s_logits = torch.randn(2, 4, 32000)
        t_logits = torch.randn(2, 4, 32000)
        labels = torch.randint(0, 32000, (2, 4))
        losses = loss_fn(s_logits, t_logits, labels)
        assert "loss" in losses
        assert losses["loss"].item() > 0

    def test_synthetic_dataset(self):
        ds = SyntheticDataset(seq_len=32, num_samples=5)
        samples = list(ds)
        assert len(samples) == 5
        for s in samples:
            assert s["input_ids"].shape == (32,)
            assert s["labels"].shape == (32,)

    def test_distillation_engine_create(self):
        t = create_validation_model()
        s = create_validation_model()
        config = DistillConfig(num_epochs=1, batch_size=2, log_interval=100)
        engine = ZkDistillationEngine(t, s, config)
        assert engine.teacher is not None
        assert engine.student is not None

    def test_train_step(self):
        t = create_validation_model()
        s = create_validation_model()
        config = DistillConfig(num_epochs=1, batch_size=2, log_interval=100)
        engine = ZkDistillationEngine(t, s, config)
        batch = {"input_ids": torch.randint(0, 100, (2, 16)),
                 "labels": torch.randint(0, 100, (2, 16))}
        losses = engine.train_step(batch)
        assert "loss" in losses
        assert losses["loss"] > 0

    def test_gguf_export(self):
        model = create_validation_model()
        path = export_gguf_proto(model, "zkAGI_test.gguf")
        assert os.path.exists(path)
        os.remove(path)
        # clean trailing gguf files
        for f in os.listdir("."):
            if f.endswith("_manifest.json") and f != "zkAGI_manifest.json":
                os.remove(f)


# ===========================================================================
# 4. METADATA TESTS
# ===========================================================================

class TestZkMetadata:
    def test_metadata_file_exists(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "arkhe_zkagi_metadata.json"
        )
        assert os.path.exists(path)
        with open(path) as f:
            meta = json.load(f)
        assert meta["architecture"] == "zkAGI"
        assert meta["num_layers"] == 48
        assert meta["num_heads"] == 32
        assert len(meta["pantheon_names"]) == 12
        assert meta["quantization"] == "Q4_K_M"
        features = meta["features"]
        assert any("Pantheon" in f for f in features)
        assert any("PLONK" in f for f in features)
        assert any("Theosis" in f for f in features)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
