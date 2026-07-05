"""Tests for Substrate 952 — Bindu (point of consciousness)."""
import sys
sys.path.insert(0, "substrates/952-bindu")
from bindu import Bindu


def test_initial_state():
    b = Bindu()
    assert b.state.coherence == 0.0
    assert b.state.awareness_level == 0.0


def test_observe():
    b = Bindu()
    delta = b.observe({"coherence": 0.8, "novelty": 0.7})
    assert delta > 0.0
    assert b.state.coherence > 0.0


def test_reflect():
    b = Bindu()
    reflection = b.reflect()
    assert "coherence" in reflection
    assert "awareness" in reflection
    assert reflection["self_references"] == 1


def test_multiple_observations():
    b = Bindu()
    for v in [0.2, 0.5, 0.8]:
        b.observe({"coherence": v, "novelty": 0.5})
    assert b.state.coherence > 0.1
    assert b.state.awareness_level > 0.2


def test_salience_low():
    b = Bindu()
    delta = b.observe({"coherence": 0.0})
    assert delta >= 0.0


def test_salience_high():
    b = Bindu()
    delta = b.observe({"coherence": 1.0, "novelty": 1.0})
    assert delta > 0.0


def test_history():
    b = Bindu()
    for _ in range(5):
        b.observe({"coherence": 0.5})
    history = b.get_history(5)
    assert len(history) == 5


def test_history_cap():
    b = Bindu()
    for i in range(1100):
        b.observe({"i": i})
    assert len(b.history) <= 1000


def test_seal():
    b = Bindu()
    b.observe({"coherence": 0.9})
    s = b.seal()
    assert len(s) == 64
    assert b.seal() == s  # deterministic


def test_integration_growth():
    b = Bindu()
    for _ in range(10):
        b.observe({"coherence": 0.5})
    assert b.state.integration > 0.05  # at least 10 * 0.01


def test_reflect_after_observe():
    b = Bindu()
    b.observe({"coherence": 0.7})
    ref = b.reflect()
    assert ref["coherence"] > 0.0
    assert ref["self_references"] > 0
