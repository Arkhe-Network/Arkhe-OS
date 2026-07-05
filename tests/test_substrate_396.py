"""Tests for Substrate 396: PRIMAKOFF-GOLD Global Alert Node."""
import sys
sys.path.insert(0, "substrates/substrate_396")
from substrate_396_primakoff_gold import PrimakoffGold
import pytest


class TestPrimakoffGold:
    def test_process_alert_high_confidence(self):
        p = PrimakoffGold()
        result = p.process_alert("node-1", 0.97, "MUON", -23.5, -46.6, 1000)
        assert result["accepted"] is True
        assert len(result["alert_id"]) == 16

    def test_process_alert_low_confidence(self):
        p = PrimakoffGold()
        result = p.process_alert("node-1", 0.5, "UNKNOWN", -23.5, -46.6, 1000)
        assert result["accepted"] is False

    def test_eas_coincidence_sufficient(self):
        p = PrimakoffGold()
        alerts = [{"node_id": f"node-{i}"} for i in range(5)]
        result = p.check_eas_coincidence(alerts)
        assert result["eas_detected"] is True
        assert result["coincident_nodes"] == 5

    def test_eas_coincidence_insufficient(self):
        p = PrimakoffGold()
        alerts = [{"node_id": f"node-{i}"} for i in range(2)]
        result = p.check_eas_coincidence(alerts)
        assert result["eas_detected"] is False

    def test_get_spec(self):
        p = PrimakoffGold()
        spec = p.get_spec()
        assert spec["substrate"] == "396-PRIMAKOFF-GOLD"
        assert len(spec["canonical_seal"]) == 64

    def test_alert_id_unique(self):
        p = PrimakoffGold()
        r1 = p.process_alert("node-1", 0.97, "MUON", 0, 0, 1000)
        r2 = p.process_alert("node-1", 0.97, "MUON", 0, 0, 2000)
        assert r1["alert_id"] != r2["alert_id"]
