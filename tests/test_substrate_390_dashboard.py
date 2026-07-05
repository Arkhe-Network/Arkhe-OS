"""Tests for Substrate 390-DASHBOARD."""
import sys
sys.path.insert(0, "substrates/substrate_390_dashboard")
from substrate_390_dashboard import DashboardDataSource, PulseEvent
import pytest


class TestPulseEvent:
    def test_to_dict(self):
        ev = PulseEvent(1000, 5000, "muon", 100.0)
        d = ev.to_dict()
        assert d["classification"] == "muon"
        assert d["amplitude_mV"] == 1000.0


class TestDashboardDataSource:
    def test_ingest_event(self):
        ds = DashboardDataSource()
        ev = ds.ingest_event(1000, 5000, "muon", 100.0)
        assert len(ds.events) == 1
        assert ev.classification == "muon"

    def test_get_stats_empty(self):
        ds = DashboardDataSource()
        stats = ds.get_stats()
        assert stats["total"] == 0

    def test_get_stats_with_events(self):
        ds = DashboardDataSource()
        ds.ingest_event(1000, 5000, "muon", 100.0)
        ds.ingest_event(800, 2000, "gamma", 0.66)
        stats = ds.get_stats()
        assert stats["total"] == 2
        assert stats["classifications"]["muon"] == 1
        assert stats["classifications"]["gamma"] == 1

    def test_get_spec(self):
        ds = DashboardDataSource()
        spec = ds.get_spec()
        assert spec["substrate"] == "390-DASHBOARD"
        assert spec["grafana_compatible"] is True
