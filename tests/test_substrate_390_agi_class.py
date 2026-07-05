"""Tests for Substrate 390-AGI-CLASS."""
import sys
sys.path.insert(0, "substrates/substrate_390_agi_class")
from substrate_390_agi_class import AGIClassifier, PulseFeatures
import pytest


class TestPulseFeatures:
    def test_to_vector(self):
        f = PulseFeatures(4000, 8000, 5, 15)
        v = f.to_vector()
        assert len(v) == 4
        assert v[0] == 4000 / 5000


class TestAGIClassifier:
    def test_generate_training_sample(self):
        c = AGIClassifier()
        sample = c.generate_training_sample("alpha")
        assert sample["true_class"] == "alpha"
        assert len(sample["features"]) == 4

    def test_train(self):
        c = AGIClassifier()
        result = c.train(200)
        assert result["accuracy"] > 0
        assert result["n_samples"] == 200

    def test_classify_returns_prediction(self):
        c = AGIClassifier()
        features = PulseFeatures(4000, 8000, 5, 15)
        result = c.classify(features)
        assert "predicted_class" in result
        assert "confidence" in result

    def test_get_spec(self):
        c = AGIClassifier()
        spec = c.get_spec()
        assert spec["substrate"] == "390-AGI-CLASS"
        assert len(spec["canonical_seal"]) == 64
        assert spec["training_accuracy"] > 0
