"""Tests for Substrate 986 — Evolution-Engine."""
import sys, pytest

sys.path.insert(0, "substrates/986-cathedral-evolution-engine")
from evolution_engine import CathedralEvolutionEngine, MutationType, FitnessDimension


class TestEvolutionEngine:
    def test_seed_population(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population([972, 973, 974, 975])
        assert len(engine.population) == 4
        for sid in [972, 973, 974, 975]:
            assert sid in engine.population

    def test_seed_population_fitness(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population([980, 981])
        for g in engine.population.values():
            assert 0.0 <= g.overall_fitness <= 1.0

    def test_mutate_parametric(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population([972])
        mut = engine.mutate(972, MutationType.PARAMETRIC)
        assert mut is not None
        if mut.success:
            assert mut.new_substrate_id is not None
            assert mut.new_substrate_id in engine.population

    def test_mutate_compositional(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population([972, 973, 974])
        mut = engine.mutate(972, MutationType.COMPOSITIONAL)
        assert mut is not None
        if mut.success:
            assert mut.target_substrate is not None

    def test_mutate_nonexistent(self):
        engine = CathedralEvolutionEngine()
        mut = engine.mutate(999, MutationType.PARAMETRIC)
        assert mut is None

    def test_select_and_extinct(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population([972, 973, 974, 975])
        extinct = engine.select_and_extinct()
        assert isinstance(extinct, list)

    def test_run_generation(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population(list(range(972, 980)))
        gen = engine.run_generation()
        assert gen.generation_number == 1
        assert len(gen.mutations) >= 0

    def test_run_multiple_generations(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population(list(range(972, 980)))
        for i in range(3):
            engine.run_generation()
        assert len(engine.generations) == 3

    def test_generate_report(self):
        engine = CathedralEvolutionEngine()
        engine.seed_population(list(range(972, 980)))
        r = engine.generate_report()
        assert "Substrato 986" in r
