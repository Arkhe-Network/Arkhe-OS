import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "arkhe"))

from l_m.luciferase_node import LuciferaseNode, LuciferaseMesh


class TestLuciferaseNode:

    def test_rate_zero_without_atp(self):
        node = LuciferaseNode("test", atp_conc_mM=0.0)
        assert node.rate() == 0.0

    def test_rate_zero_without_luciferin(self):
        node = LuciferaseNode("test", luciferin_conc_mM=0.0)
        assert node.rate() == 0.0

    def test_rate_positive_with_substrates(self):
        node = LuciferaseNode("test", luciferin_conc_mM=1.0, atp_conc_mM=2.0)
        assert node.rate() > 0.0

    def test_photon_flux_positive(self):
        node = LuciferaseNode("test", luciferin_conc_mM=1.0, atp_conc_mM=2.0)
        assert node.photon_flux() > 0.0

    def test_phi_c_bounded(self):
        node = LuciferaseNode("test")
        assert 0.0 <= node.phi_c() <= 1.0

    def test_phi_c_increases_with_quantum_yield(self):
        low = LuciferaseNode("low", quantum_yield=0.5)
        high = LuciferaseNode("high", quantum_yield=0.99)
        assert high.phi_c() > low.phi_c()

    def test_phi_c_increases_with_atp(self):
        low = LuciferaseNode("low", atp_conc_mM=0.1)
        high = LuciferaseNode("high", atp_conc_mM=5.0)
        assert high.phi_c() > low.phi_c()

    def test_emit_pulse_generates_seal(self):
        node = LuciferaseNode("test")
        pulse = node.emit_pulse()
        assert "seal" in pulse
        assert len(pulse["seal"]) == 64

    def test_emit_pulse_increases_flash_count(self):
        node = LuciferaseNode("test")
        node.emit_pulse()
        assert node._flash_count == 1

    def test_emit_pulse_increases_total_photons(self):
        node = LuciferaseNode("test")
        node.emit_pulse()
        assert node._total_photons_emitted > 0.0

    def test_golden_pulse_duration(self):
        node = LuciferaseNode("test")
        pulse = node.emit_golden_pulse()
        expected = 5.0 * node.PHI
        assert abs(pulse["duration_ms"] - expected) < 0.01

    def test_recharge_atp(self):
        node = LuciferaseNode("test", atp_conc_mM=1.0)
        node.recharge_atp(1.0)
        assert node.atp_conc_mM == 2.0

    def test_recharge_atp_limited(self):
        node = LuciferaseNode("test", atp_conc_mM=9.0)
        node.recharge_atp(5.0)
        assert node.atp_conc_mM <= 10.0

    def test_consume_luciferin(self):
        node = LuciferaseNode("test", luciferin_conc_mM=2.0)
        node.consume_luciferin(1.0)
        assert node.luciferin_conc_mM == 1.0

    def test_consume_luciferin_non_negative(self):
        node = LuciferaseNode("test", luciferin_conc_mM=0.5)
        node.consume_luciferin(1.0)
        assert node.luciferin_conc_mM == 0.0

    def test_status_complete(self):
        node = LuciferaseNode("test")
        status = node.get_status()
        required = [
            "node_id", "phi_c", "photon_flux", "rate_uM_s",
            "quantum_yield", "total_photons_emitted", "flash_count",
            "atp_mM", "luciferin_mM", "canonical_invariants",
        ]
        for field in required:
            assert field in status
        invariants = status["canonical_invariants"]
        assert "ghost" in invariants
        assert "loopseal" in invariants
        assert "gap_max" in invariants
        assert "phi" in invariants
        assert "alpha_inv" in invariants

    def test_pulse_history(self):
        node = LuciferaseNode("test")
        node.emit_pulse()
        node.emit_pulse()
        history = node.get_pulse_history()
        assert len(history) == 2

    def test_quantum_yield_above_ghost(self):
        node = LuciferaseNode("test")
        assert node.quantum_yield > node.GHOST

    def test_flash_duration_in_range(self):
        node = LuciferaseNode("test")
        assert 5.0 <= node.flash_duration_ms <= 10.0


class TestLuciferaseMesh:

    def test_register_node(self):
        mesh = LuciferaseMesh()
        node = LuciferaseNode("N1")
        mesh.register_node(node)
        assert "N1" in mesh.nodes

    def test_connect_nodes(self):
        mesh = LuciferaseMesh()
        mesh.register_node(LuciferaseNode("N1"))
        mesh.register_node(LuciferaseNode("N2"))
        mesh.connect_nodes("N1", "N2")
        assert "N2" in mesh.adjacency["N1"]
        assert "N1" in mesh.adjacency["N2"]

    def test_broadcast_detects_neighbors(self):
        mesh = LuciferaseMesh()
        mesh.register_node(LuciferaseNode("N1", atp_conc_mM=5.0))
        mesh.register_node(LuciferaseNode("N2", atp_conc_mM=5.0))
        mesh.connect_nodes("N1", "N2")
        detections = mesh.broadcast_pulse("N1")
        assert len(detections) == 1
        assert detections[0]["detector"] == "N2"

    def test_broadcast_skips_weak_nodes(self):
        mesh = LuciferaseMesh()
        mesh.register_node(LuciferaseNode("N1", atp_conc_mM=5.0))
        mesh.register_node(LuciferaseNode("N2", quantum_yield=0.3, luciferin_conc_mM=0.01, atp_conc_mM=0.01))
        mesh.connect_nodes("N1", "N2")
        detections = mesh.broadcast_pulse("N1")
        assert len(detections) == 0

    def test_mesh_status_complete(self):
        mesh = LuciferaseMesh()
        for i in range(3):
            mesh.register_node(LuciferaseNode(f"N{i}"))
        status = mesh.get_mesh_status()
        assert status["total_nodes"] == 3
        assert "average_phi_c" in status
        assert "total_photons_emitted" in status


class TestCanonicalInvariants327:

    def test_ghost_value(self):
        node = LuciferaseNode("test")
        assert abs(node.GHOST - math.sqrt(3) / 3) < 1e-9

    def test_loopseal_value(self):
        node = LuciferaseNode("test")
        assert abs(node.LOOPSEAL - math.pi / 9) < 1e-9

    def test_phi_value(self):
        node = LuciferaseNode("test")
        expected = (1 + math.sqrt(5)) / 2
        assert abs(node.PHI - expected) < 1e-15

    def test_alpha_inverse(self):
        node = LuciferaseNode("test")
        assert abs(node.ALPHA_INV - 137.036) < 0.001

    def test_quantum_yield_above_ghost_threshold(self):
        node = LuciferaseNode("test")
        assert node.quantum_yield > node.GHOST
        assert node.quantum_yield >= 0.88
