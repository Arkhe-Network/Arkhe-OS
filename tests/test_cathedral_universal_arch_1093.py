import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cathedral_universal_arch_1093 import (
    ArchitectureParadigm, MaturityLevel, Deity,
    ArchitectureSubstrate, CathedralArchitectureCatalog,
    demo_universal_architecture,
)


class TestArchitectureParadigm:

    def test_has_20_values(self):
        assert len(ArchitectureParadigm) == 20

    def test_key_paradigms_present(self):
        names = {e.name for e in ArchitectureParadigm}
        assert "MONOLITHIC" in names
        assert "MICROSERVICES" in names
        assert "EVENT_DRIVEN" in names
        assert "SERVERLESS" in names
        assert "CQRS" in names
        assert "SHARDING" in names
        assert "LAYERED" in names
        assert "PEER_TO_PEER" in names
        assert "WEBASSEMBLY" in names
        assert "NEUROMORPHIC" in names
        assert "QUANTUM" in names
        assert "CONTAINER_ORCHESTRATION" in names
        assert "SERVICE_MESH" in names
        assert "DATA_MESH" in names
        assert "GRAPHQL_FEDERATION" in names
        assert "GRPC" in names
        assert "REACTIVE" in names
        assert "DOMAIN_DRIVEN" in names
        assert "HEXAGONAL" in names
        assert "CIRCUIT_BREAKER" in names


class TestMaturityLevel:

    def test_has_4_values(self):
        assert len(MaturityLevel) == 4

    def test_values(self):
        assert MaturityLevel.RESEARCH.name == "RESEARCH"
        assert MaturityLevel.PILOT.name == "PILOT"
        assert MaturityLevel.PRODUCTION.name == "PRODUCTION"
        assert MaturityLevel.CANONIZED.name == "CANONIZED"


class TestDeity:

    def test_has_10_values(self):
        assert len(Deity) == 10

    def test_deity_values(self):
        assert Deity.HEFESTO.value == "Hefesto"
        assert Deity.ATENA.value == "Atena"
        assert Deity.HERMES.value == "Hermes"
        assert Deity.MNEMOSYNE.value == "Mnemosyne"
        assert Deity.PROMETEU.value == "Prometeu"
        assert Deity.CRONOS.value == "Cronos"
        assert Deity.GAIA.value == "Gaia"
        assert Deity.APOLLO.value == "Apolo"
        assert Deity.DIONISIO.value == "Dionisio"
        assert Deity.NEMESIS.value == "Nemesis"


class TestArchitectureSubstrate:

    def test_create_with_all_fields(self):
        s = ArchitectureSubstrate(
            id="1093.99", name="TEST_ARCH",
            paradigm=ArchitectureParadigm.MICROSERVICES,
            maturity=MaturityLevel.CANONIZED,
            deities=[Deity.HERMES, Deity.ATENA],
            description="Test description",
            equation="Test = 1",
            components=["comp1"], patterns=["pattern1"],
            anti_patterns=["antip1"],
            scalability_score=0.8, complexity_score=0.5,
            resilience_score=0.9,
        )
        assert s.id == "1093.99"
        assert s.name == "TEST_ARCH"
        assert s.paradigm == ArchitectureParadigm.MICROSERVICES
        assert s.maturity == MaturityLevel.CANONIZED
        assert len(s.deities) == 2
        assert s.scalability_score == 0.8
        assert s.complexity_score == 0.5
        assert s.resilience_score == 0.9

    def test_seal_auto_generated(self):
        s = ArchitectureSubstrate(
            id="1093.98", name="NO_SEAL",
            paradigm=ArchitectureParadigm.MONOLITHIC,
            maturity=MaturityLevel.PRODUCTION,
            deities=[Deity.HEFESTO],
            description="desc", equation="eq",
            components=[], patterns=[], anti_patterns=[],
            scalability_score=0.5, complexity_score=0.5,
            resilience_score=0.5,
        )
        assert s.seal != ""
        assert s.seal.startswith("0x")
        assert len(s.seal) == 34  # 0x + 32 hex chars

    def test_custom_seal_not_overwritten(self):
        s = ArchitectureSubstrate(
            id="1093.97", name="CUSTOM_SEAL",
            paradigm=ArchitectureParadigm.SERVERLESS,
            maturity=MaturityLevel.PILOT,
            deities=[Deity.GAIA],
            description="desc", equation="eq",
            components=[], patterns=[], anti_patterns=[],
            scalability_score=0.5, complexity_score=0.5,
            resilience_score=0.5,
            seal="0xcustom"
        )
        assert s.seal == "0xcustom"

    def test_to_dict_format(self):
        s = ArchitectureSubstrate(
            id="1093.96", name="TO_DICT",
            paradigm=ArchitectureParadigm.EVENT_DRIVEN,
            maturity=MaturityLevel.RESEARCH,
            deities=[Deity.HERMES, Deity.CRONOS],
            description="Dict test", equation="D={}",
            components=["a"], patterns=["b"], anti_patterns=["c"],
            scalability_score=0.6, complexity_score=0.7,
            resilience_score=0.8,
        )
        d = s.to_dict()
        assert d["id"] == "1093.96"
        assert d["name"] == "TO_DICT"
        assert d["paradigm"] == "EVENT_DRIVEN"
        assert d["maturity"] == "RESEARCH"
        assert d["deities"] == ["Hermes", "Cronos"]
        assert isinstance(d["scalability_score"], float)
        assert "seal" in d


class TestCathedralArchitectureCatalog:

    def test_init_has_20_substrates(self):
        c = CathedralArchitectureCatalog()
        assert len(c.substrates) == 20

    def test_get_by_id(self):
        c = CathedralArchitectureCatalog()
        s = c.get("1093.1")
        assert s is not None
        assert s.name == "MONOLITHIC_MODULAR"
        assert s.id == "1093.1"

    def test_get_nonexistent(self):
        c = CathedralArchitectureCatalog()
        assert c.get("9999.99") is None

    def test_by_paradigm(self):
        c = CathedralArchitectureCatalog()
        monolithic = c.by_paradigm(ArchitectureParadigm.MONOLITHIC)
        assert len(monolithic) == 1
        assert monolithic[0].id == "1093.1"

    def test_by_maturity(self):
        c = CathedralArchitectureCatalog()
        canonized = c.by_maturity(MaturityLevel.CANONIZED)
        assert len(canonized) >= 8
        assert all(s.maturity == MaturityLevel.CANONIZED for s in canonized)

    def test_by_deity(self):
        c = CathedralArchitectureCatalog()
        hefesto = c.by_deity(Deity.HEFESTO)
        assert len(hefesto) >= 1
        assert all(Deity.HEFESTO in s.deities for s in hefesto)

    def test_substrate_1093_1_monolithic_modular(self):
        c = CathedralArchitectureCatalog()
        s = c.get("1093.1")
        assert s.paradigm == ArchitectureParadigm.MONOLITHIC
        assert s.maturity == MaturityLevel.CANONIZED
        assert Deity.HEFESTO in s.deities
        assert Deity.ATENA in s.deities

    def test_substrate_1093_2_microservices(self):
        c = CathedralArchitectureCatalog()
        s = c.get("1093.2")
        assert s.paradigm == ArchitectureParadigm.MICROSERVICES
        assert s.maturity == MaturityLevel.CANONIZED
        assert Deity.HERMES in s.deities

    def test_substrate_1093_8_peer_to_peer(self):
        c = CathedralArchitectureCatalog()
        s = c.get("1093.8")
        assert s.paradigm == ArchitectureParadigm.PEER_TO_PEER
        assert s.maturity == MaturityLevel.CANONIZED
        assert len(s.deities) == 3

    def test_cross_links_non_empty(self):
        c = CathedralArchitectureCatalog()
        for sid in ["1093.1", "1093.2", "1093.8"]:
            s = c.get(sid)
            assert len(s.cross_links) > 0, f"{sid} has no cross links"

    def test_get_telemetry_keys(self):
        c = CathedralArchitectureCatalog()
        t = c.get_telemetry()
        assert t["module"] == "CathedralArchitectureCatalog"
        assert t["version"] == "1.0.0"
        assert t["substrate"] == "1093"
        assert "seal" in t
        assert t["total_architectures"] == 20
        assert "paradigm_distribution" in t
        assert "maturity_distribution" in t
        assert "deity_distribution" in t
        assert "average_scores" in t
        assert "substrates" in t

    def test_telemetry_average_scores(self):
        c = CathedralArchitectureCatalog()
        t = c.get_telemetry()
        avg = t["average_scores"]
        assert "scalability" in avg
        assert "complexity" in avg
        assert "resilience" in avg
        assert 0.0 <= avg["scalability"] <= 1.0
        assert 0.0 <= avg["complexity"] <= 1.0
        assert 0.0 <= avg["resilience"] <= 1.0

    def test_all_scores_within_range(self):
        c = CathedralArchitectureCatalog()
        for s in c.substrates.values():
            assert 0.0 <= s.scalability_score <= 1.0, f"{s.id} scalability out of range"
            assert 0.0 <= s.complexity_score <= 1.0, f"{s.id} complexity out of range"
            assert 0.0 <= s.resilience_score <= 1.0, f"{s.id} resilience out of range"

    def test_demo_runs_without_error(self):
        result = demo_universal_architecture()
        assert result["total_architectures"] == 20
        assert "average_scores" in result
