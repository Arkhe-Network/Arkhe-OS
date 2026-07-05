"""Tests for Substrate 392: AGI + FPGA-DAQ Integration."""
import sys, math
sys.path.insert(0, "substrates/substrate_392")
from substrate_392_agi_fpga import (
    MCPFPGAServer, AGIFPGA, AGIConsensus, run_substrate_392, GHOST, PHI,
)
import pytest


class TestMCPFPGAServer:
    def test_read_event_structure(self):
        s = MCPFPGAServer()
        ev = s.read_event()
        assert "timestamp_ns" in ev
        assert "amplitude" in ev
        assert "integral" in ev
        assert ev["amplitude"] >= 0
        assert ev["integral"] >= 0

    def test_get_status(self):
        s = MCPFPGAServer()
        st = s.get_status()
        assert st["event_count"] == 0
        assert st["pcie_link"] == "Gen2 x4 OK"

    def test_event_count_increments(self):
        s = MCPFPGAServer()
        s.read_event()
        s.read_event()
        assert s.event_count == 2


class TestAGIFPGA:
    def test_muon_agent_classifies_muon_event(self):
        agent = AGIFPGA("MUON-01", "muon")
        result = agent.classify_event({"amplitude": 800, "integral": 5000})
        assert result["class"] == "MUON"
        assert result["confidence"] > 0.9

    def test_photon_agent_classifies_photon_event(self):
        agent = AGIFPGA("PHOT-01", "photon")
        result = agent.classify_event({"amplitude": 200, "integral": 700})
        assert result["class"] == "PHOTON"

    def test_trigger_agent_triggers_on_high_amp(self):
        agent = AGIFPGA("TRIG-01", "trigger")
        result = agent.classify_event({"amplitude": 600, "integral": 3000})
        assert result["class"] == "TRIGGER"
        assert result["action"] == "SEND_TO_PRIMAKOFF"

    def test_trigger_agent_no_trigger_on_low_amp(self):
        agent = AGIFPGA("TRIG-01", "trigger")
        result = agent.classify_event({"amplitude": 50, "integral": 200})
        assert result is None

    def test_calorimetry_returns_energy(self):
        agent = AGIFPGA("CAL-01", "calorimetry")
        result = agent.classify_event({"amplitude": 300, "integral": 2000})
        assert result["energy_mev"] == 20.0


class TestAGIConsensus:
    def test_consensus_majority(self):
        agents = [
            AGIFPGA(f"A{i}", "muon" if i < 7 else "electron")
            for i in range(10)
        ]
        engine = AGIConsensus(agents)
        result = engine.classify({"amplitude": 800, "integral": 5000})
        assert result["class"] == "MUON"
        assert result["quorum_reached"]

    def test_consensus_unknown_if_no_expertise_matches(self):
        agents = [AGIFPGA("A0", "neutron")]
        engine = AGIConsensus(agents)
        result = engine.classify({"amplitude": 800, "integral": 5000})
        assert result["class"] == "UNKNOWN"


class TestRunSubstrate:
    def test_run_returns_metrics(self):
        result = run_substrate_392(100)
        assert result["phi_c"] > 0
        assert result["n_events"] == 100
        assert isinstance(result["triggers_sent"], int)
        assert len(result["canonical_seal"]) == 64

    def test_ghost_constant(self):
        assert abs(GHOST - 0.57735) < 1e-4

    def test_phi_constant(self):
        assert abs(PHI - 1.61803) < 1e-4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
