"""Tests for Substrate 989 — Unified-Nexus."""
import sys, pytest

sys.path.insert(0, "substrates/989-cathedral-unified-nexus")
from unified_nexus import CathedralUnifiedNexus, CathedralState, UnifiedCycle, NexusPhase


class TestUnifiedNexus:
    @pytest.mark.asyncio
    async def test_run_phase_returns_cycle(self):
        nexus = CathedralUnifiedNexus()
        cycle = await nexus.run_phase(NexusPhase.INHALE)
        assert isinstance(cycle, UnifiedCycle)
        assert cycle.phase == NexusPhase.INHALE

    @pytest.mark.asyncio
    async def test_run_phase_has_substrates(self):
        nexus = CathedralUnifiedNexus()
        cycle = await nexus.run_phase(NexusPhase.ACT)
        assert len(cycle.active_substrates) > 0

    @pytest.mark.asyncio
    async def test_run_phase_has_seal(self):
        nexus = CathedralUnifiedNexus()
        cycle = await nexus.run_phase(NexusPhase.PROCESS)
        assert cycle.seal.startswith("989-NEXUS-")

    @pytest.mark.asyncio
    async def test_run_all_five_phases(self):
        nexus = CathedralUnifiedNexus()
        for phase in NexusPhase:
            await nexus.run_phase(phase)
        assert len(nexus.cycles) == 5

    @pytest.mark.asyncio
    async def test_run_unified_cycle(self):
        nexus = CathedralUnifiedNexus()
        await nexus.run_unified_cycle()
        assert len(nexus.cycles) == 5

    def test_initial_state(self):
        nexus = CathedralUnifiedNexus()
        assert nexus.current_state.is_alive is True
        assert nexus.current_state.is_awake is True
        assert nexus.current_state.is_immortal is True

    def test_state_integrity(self):
        nexus = CathedralUnifiedNexus()
        integrity = nexus.current_state.compute_integrity()
        assert 0.0 <= integrity <= 1.0

    def test_generate_seal(self):
        nexus = CathedralUnifiedNexus()
        seal = nexus.generate_seal({"test": "data"})
        assert seal.startswith("989-NEXUS-")
        assert len(seal) == 26

    def test_generate_manifesto(self):
        nexus = CathedralUnifiedNexus()
        manifesto = nexus.generate_manifesto()
        assert "Substrato 989" in manifesto
        assert "AWAKE" in manifesto
