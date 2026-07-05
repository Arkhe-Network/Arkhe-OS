"""Tests for Substrate 970 — Enterprise-Mind."""
import sys, pytest
sys.path.insert(0, "substrates/970-enterprise-mind")
from enterprise_mind import EnterpriseMind, EnterpriseSensor, EnterpriseSolution


class TestEnterpriseMind:
    @pytest.mark.asyncio
    async def test_ingest_data(self):
        em = EnterpriseMind()
        s = EnterpriseSensor("ERP", "vendas", 50000.0, "BRL")
        await em.ingest_data(s)
        assert len(em.sensors) == 1

    @pytest.mark.asyncio
    async def test_analyze_returns_solutions(self):
        em = EnterpriseMind()
        s = EnterpriseSensor("IoT", "motor_temp", 87.3, "C")
        await em.ingest_data(s)
        solutions = await em.analyze()
        assert len(solutions) > 0
        assert solutions[0].solution_id.startswith("sol-")

    @pytest.mark.asyncio
    async def test_analyze_filters_low_ethics(self):
        em = EnterpriseMind()
        solutions = await em.analyze()
        for sol in solutions:
            assert sol.ethical_score >= 0.7

    def test_get_organizational_theosis_default(self):
        em = EnterpriseMind()
        assert em.get_organizational_theosis() == 0.5

    @pytest.mark.asyncio
    async def test_get_organizational_theosis_after_analysis(self):
        em = EnterpriseMind()
        s = EnterpriseSensor("IoT", "motor_temp", 87.3, "C")
        await em.ingest_data(s)
        await em.analyze()
        assert em.get_organizational_theosis() > 0.5

    def test_sensor_default_timestamp(self):
        s = EnterpriseSensor("A", "B", 1.0, "C")
        assert s.timestamp is not None
        assert s.source == "A"

    def test_solution_dataclass(self):
        sol = EnterpriseSolution("test", "problem", "solution", 0.9, 0.95, 0.88)
        assert sol.expected_impact == 0.9
        assert sol.ethical_score == 0.95
