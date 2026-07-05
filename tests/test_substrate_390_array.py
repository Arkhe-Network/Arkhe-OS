"""Tests for Substrate 390-ARRAY."""
import sys
sys.path.insert(0, "substrates/substrate_390_array")
from substrate_390_array import DetectorArray, ArrayChannel
import pytest


class TestArrayChannel:
    def test_record_event(self):
        ch = ArrayChannel(0, 0, 0, 0)
        ch.record_event(1000.0)
        assert len(ch.events) == 1


class TestDetectorArray:
    def test_initialization(self):
        arr = DetectorArray(4, 1.0)
        assert len(arr.channels) == 4
        assert arr.spacing_m == 1.0

    def test_triangulation_insufficient(self):
        arr = DetectorArray(4, 1.0)
        result = arr.triangulate([1000.0, 1001.0])
        assert result["source_detected"] is False

    def test_simulate_event(self):
        arr = DetectorArray(4, 1.0)
        result = arr.simulate_event(2.0, 1.5)
        assert "source_detected" in result

    def test_get_spec(self):
        arr = DetectorArray(4, 1.0)
        spec = arr.get_spec()
        assert spec["substrate"] == "390-ARRAY"
        assert spec["channels"] == 4
        assert len(spec["canonical_seal"]) == 64
