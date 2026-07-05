"""Tests for Substrate 953 — Tanmatra (Embodied Sensory/Motor)."""
import sys
sys.path.insert(0, "substrates/953-tanmatra")
from tanmatra import TanmatraInterface


def test_register_sensor():
    t = TanmatraInterface()
    sid = t.register_sensor("camera_1", "vision", {"resolution": "1920x1080"})
    assert sid.startswith("sensor-")
    assert t.get_sensor_count() == 1


def test_sense_all():
    t = TanmatraInterface()
    frame = t.sense(["vision", "audio", "touch"])
    assert frame.vision is not None
    assert frame.audio is not None
    assert frame.touch is not None


def test_sense_partial():
    t = TanmatraInterface()
    frame = t.sense(["vision"])
    assert frame.vision is not None
    assert frame.audio is None


def test_sense_none():
    t = TanmatraInterface()
    frame = t.sense()
    assert frame.frame_id is not None


def test_act():
    t = TanmatraInterface()
    result = t.act({"type": "move_arm", "angles": [0, 90, 45]})
    assert result["status"] == "executed"
    assert "action_id" in result


def test_multiple_sensors():
    t = TanmatraInterface()
    t.register_sensor("mic", "audio")
    t.register_sensor("cam", "vision")
    t.register_sensor("touch", "haptic")
    assert t.get_sensor_count() == 3


def test_frame_count():
    t = TanmatraInterface()
    t.sense(["vision"])
    t.sense(["audio"])
    assert t.get_frame_count() == 2


def test_seal():
    t = TanmatraInterface()
    t.register_sensor("test", "test")
    t.sense(["vision"])
    s = t.seal()
    assert len(s) == 64


def test_smell_taste():
    t = TanmatraInterface()
    frame = t.sense(["smell", "taste"])
    assert frame.smell is not None
    assert frame.taste is not None


def test_frame_structure():
    t = TanmatraInterface()
    frame = t.sense(["vision"])
    assert hasattr(frame, "frame_id")
    assert hasattr(frame, "timestamp")
