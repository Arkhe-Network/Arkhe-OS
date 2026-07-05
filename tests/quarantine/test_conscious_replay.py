"""Tests for Substrate 951 — Conscious-Replay."""
import sys
sys.path.insert(0, "substrates/951-conscious-replay")
from conscious_replay import ConsciousReplay


def test_record():
    cr = ConsciousReplay()
    eid = cr.record({"type": "thought", "content": "hello"})
    assert eid and len(eid) == 16


def test_sleep_cycle():
    cr = ConsciousReplay()
    cr.record({"type": "a", "value": 1}, coherence=0.8)
    cr.record({"type": "b", "value": 2}, coherence=0.6)
    cr.record({"type": "c", "value": 3}, coherence=0.9)
    dream = cr.sleep_cycle()
    assert dream.id and dream.cycle_id


def test_novelty():
    cr = ConsciousReplay()
    cr.record({"type": "x", "value": 10}, coherence=0.9)
    dream = cr.sleep_cycle()
    assert 0.0 <= dream.novelty_score <= 1.0


def test_consolidation():
    cr = ConsciousReplay()
    cr.record({"type": "x", "value": 1})
    assert not list(cr.buffer.values())[0].consolidated
    cr.sleep_cycle()
    assert list(cr.buffer.values())[0].consolidated


def test_stats():
    cr = ConsciousReplay()
    cr.record({"type": "x", "value": 1})
    cr.sleep_cycle()
    stats = cr.get_stats()
    assert stats["cycle_count"] >= 1
    assert stats["buffer_size"] >= 1


def test_capacity():
    cr = ConsciousReplay(capacity=1)
    cr.record({"type": "a"})
    cr.record({"type": "b"})
    assert len(cr.buffer) <= 1


def test_synthesis():
    cr = ConsciousReplay()
    cr.record({"color": "red"})
    cr.record({"color": "blue"})
    dream = cr.sleep_cycle()
    assert "color" in dream.synthesized_data


def test_empty_synthesis():
    cr = ConsciousReplay()
    cr.record({"x": 1})
    dream = cr.sleep_cycle()
    assert dream.synthesized_data is not None


def test_dream_seal():
    cr = ConsciousReplay()
    cr.record({"type": "seal_test"})
    dream = cr.sleep_cycle()
    assert len(dream.seal) == 64


def test_multiple_cycles():
    cr = ConsciousReplay()
    for i in range(5):
        cr.record({"i": i})
    for _ in range(3):
        cr.sleep_cycle()
    assert cr.cycle_count == 3


def test_replay_count():
    cr = ConsciousReplay()
    cr.record({"type": "test"}, coherence=1.0)
    for _ in range(2):
        cr.sleep_cycle()
        cr.record({"type": "extra"})
    assert all(e.replay_count >= 1 or not e.consolidated for e in cr.buffer.values())
