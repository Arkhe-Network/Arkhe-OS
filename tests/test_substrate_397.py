"""Tests for Substrate 397: MESH-WORLD Global Mesh Network."""
import sys, math
sys.path.insert(0, "substrates/substrate_397")
from substrate_397_mesh_world import SmartphoneNode, MeshNetwork, GHOST, PHI
import pytest


class TestSmartphoneNode:
    def test_sensors_initialized(self):
        node = SmartphoneNode(0, 0, 0)
        assert len(node.sensors) == 6
        for s in ["cmos", "wifi", "bluetooth", "5g", "accel", "mic"]:
            assert s in node.sensors

    def test_detect_event_returns_list(self):
        node = SmartphoneNode(0, 0, 0)
        hits = node.detect_event()
        assert isinstance(hits, list)

    def test_classify_noise(self):
        node = SmartphoneNode(0, 0, 0)
        cls = node.classify_multimodal([])
        assert cls["class"] == "NOISE"

    def test_classify_unknown(self):
        node = SmartphoneNode(0, 0, 0)
        cls = node.classify_multimodal(["cmos"])
        assert cls["class"] == "UNKNOWN"

    def test_classify_muon(self):
        node = SmartphoneNode(0, 0, 0)
        cls = node.classify_multimodal(["cmos", "wifi"])
        assert cls["class"] == "MUON"
        assert cls["confidence"] >= 0.85

    def test_classify_muon_high_confidence(self):
        node = SmartphoneNode(0, 0, 0)
        cls = node.classify_multimodal(["cmos", "wifi", "bluetooth", "5g"])
        assert cls["confidence"] <= 0.98


class TestMeshNetwork:
    def test_initialization(self):
        mesh = MeshNetwork(100, 42)
        assert len(mesh.nodes) == 100
        assert len(mesh.nodes[0].neighbors) == 5

    def test_simulation_runs(self):
        mesh = MeshNetwork(200, 42)
        result = mesh.run_simulation(50)
        assert result["n_nodes"] == 200
        assert result["n_rays"] == 50
        assert result["total_detections"] >= 0

    def test_phi_c_in_range(self):
        mesh = MeshNetwork(500, 42)
        result = mesh.run_simulation(100)
        assert 0.9 <= result["phi_c"] <= 1.0

    def test_canonical_seal_length(self):
        mesh = MeshNetwork(100, 42)
        result = mesh.run_simulation(10)
        assert len(result["canonical_seal"]) == 64

    def test_global_events_are_recorded(self):
        mesh = MeshNetwork(500, 42)
        result = mesh.run_simulation(100)
        assert result["global_events"] >= 0

    def test_get_spec_structure(self):
        mesh = MeshNetwork(100, 42)
        spec = mesh.get_spec()
        assert spec["substrate"] == "397-MESH-WORLD"
        assert "sensor_channels" in spec
        assert "gossip_protocol" in spec
        assert "federated_learning" in spec
        assert "projects_integrated" in spec

    def test_reproducibility(self):
        r1 = MeshNetwork(100, 42).run_simulation(50)
        r2 = MeshNetwork(100, 42).run_simulation(50)
        assert r1["total_detections"] == r2["total_detections"]
        assert r1["phi_c"] == r2["phi_c"]

    def test_ghost_constant(self):
        assert abs(GHOST - 0.57735) < 1e-4
