import pytest
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "arkhe"))

from l_m.orkut_2 import (
    Orkut2, Pesquisador, Comunidade, Scrap, Depoimento, Evento,
    FeedOrkut, AssistenteAGI,
    GHOST, LOOPSEAL, GAP_MAX, PHI, ALPHA_INV,
    extract_latex, phi_c_weight, sha3_seal,
)


class TestInvariants:

    def test_ghost(self):
        assert math.isclose(GHOST, math.sqrt(3) / 3)

    def test_loopseal(self):
        assert math.isclose(LOOPSEAL, math.pi / 9)

    def test_gap_max(self):
        assert GAP_MAX < 1.0

    def test_phi(self):
        assert math.isclose(PHI, (1 + math.sqrt(5)) / 2)

    def test_alpha_inv(self):
        assert math.isclose(ALPHA_INV, 137.035999084)


class TestUtils:

    def test_extract_latex_single(self):
        r = extract_latex("Phi_C=$0.344$")
        assert len(r) == 1
        assert "0.344" in r[0][0] or "0.344" in r[0][1]

    def test_extract_latex_double(self):
        r = extract_latex("Equation: $$E=mc^2$$")
        assert len(r) >= 1

    def test_extract_latex_none(self):
        r = extract_latex("Just plain text")
        assert r == []

    def test_phi_c_weight_full_consensus(self):
        w = phi_c_weight(10, 0)
        assert math.isclose(w, GAP_MAX)

    def test_phi_c_weight_split(self):
        w = phi_c_weight(5, 5)
        assert math.isclose(w, GHOST, abs_tol=0.01)

    def test_phi_c_weight_zero(self):
        w = phi_c_weight(0, 0)
        assert math.isclose(w, GHOST)

    def test_sha3_seal_length(self):
        seal = sha3_seal({"test": "data"})
        assert len(seal) == 64


class TestPesquisador:

    def test_create_with_orcid(self):
        p = Pesquisador("orcid:0000-0002-1234-5678", "Maria", "USP", "Física")
        assert p.orcid == "orcid:0000-0002-1234-5678"
        assert p.name == "Maria"

    def test_create_adds_prefix(self):
        p = Pesquisador("0000-0002-1234-5678", "João", "UNICAMP")
        assert p.orcid.startswith("orcid:")

    def test_token_arkhe_generated(self):
        p = Pesquisador("orcid:0000-0002-1234-5678", "Maria", "USP")
        assert len(p.token_arkhe) == 64

    def test_initial_phi_c(self):
        p = Pesquisador("orcid:test", "Test", "Inst")
        assert math.isclose(p.phi_c, GHOST)

    def test_phi_c_trend_stable_initially(self):
        p = Pesquisador("orcid:test", "Test", "Inst")
        assert p.phi_c_trend == "stable"

    def test_add_phi_c_reading(self):
        p = Pesquisador("orcid:test", "Test", "Inst")
        p.add_phi_c_reading(0.7)
        assert p.phi_c == 0.7

    def test_phi_c_trend_rising(self):
        p = Pesquisador("orcid:test", "Test", "Inst")
        for v in [0.58, 0.60, 0.63, 0.65, 0.68]:
            p.add_phi_c_reading(v)
        assert p.phi_c_trend == "rising"

    def test_add_medalha(self):
        p = Pesquisador("orcid:test", "Test", "Inst")
        m = p.add_medalha("Artigo Publicado", "Paper na Nature")
        assert len(p.medalhas) == 1
        assert len(m.seal) == 64

    def test_profile_contains_keys(self):
        p = Pesquisador("orcid:test", "Test", "Inst", "Biofotônica")
        profile = p.to_profile()
        assert profile["name"] == "Test"
        assert profile["area"] == "Biofotônica"
        assert "phi_c" in profile


class TestScrap:

    def test_create_basic(self):
        s = Scrap(scrap_id="S-001", author_orcid="orcid:test",
                   content="Meu primeiro scrap!")
        assert s.scrap_id == "S-001"
        assert len(s.seal) == 64

    def test_latex_detection(self):
        s = Scrap(scrap_id="S-002", author_orcid="orcid:test",
                   content="Phi_C=$0.344$")
        assert s.has_latex() is True

    def test_no_latex(self):
        s = Scrap(scrap_id="S-003", author_orcid="orcid:test",
                   content="Sem fórmulas aqui")
        assert s.has_latex() is False

    def test_double_latex(self):
        s = Scrap(scrap_id="S-004", author_orcid="orcid:test",
                   content="$$E=mc^2$$ and $\\lambda_2$")
        assert s.has_latex()

    def test_explicit_seal(self):
        s = Scrap(scrap_id="S-005", author_orcid="orcid:test",
                   content="teste", seal="custom-seal")
        assert s.seal == "custom-seal"


class TestDepoimento:

    def test_create(self):
        d = Depoimento("D-001", "orcid:a", "orcid:b", "Ótimo trabalho!")
        assert d.from_orcid == "orcid:a"
        assert d.to_orcid == "orcid:b"
        assert len(d.seal) == 64

    def test_different_from_to(self):
        d = Depoimento("D-002", "orcid:a", "orcid:b", "Colaboração excelente!", "proj-1")
        assert d.from_orcid != d.to_orcid


class TestEvento:

    def test_create(self):
        e = Evento("E-001", "Defesa de Mestrado", "defesa",
                    "biofotonica", "2026-06-15", "orcid:test")
        assert e.title == "Defesa de Mestrado"
        assert len(e.seal) == 64

    def test_confirm_presenca(self):
        e = Evento("E-002", "Seminário", "seminario",
                    "geral", "2026-07-01", "orcid:test")
        seal = e.confirm_presenca("orcid:conv")
        assert "orcid:conv" in e.confirmed_orcids
        assert len(seal) == 64


class TestComunidade:

    def test_create(self):
        c = Comunidade("biofotonica", "Biofotônica", "Pesquisa em biofotônica",
                        "orcid:founder")
        assert c.community_id == "biofotonica"
        assert len(c.constitution_seal) == 64

    def test_default_rules(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        assert len(c.rules) == 4

    def test_add_member(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        assert c.add_member("orcid:m1") is True
        assert "orcid:m1" in c.members

    def test_phi_c_average(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        c.add_member("orcid:m2", 0.7)
        assert c.phi_c > 0

    def test_post_scrap(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        s = c.post_scrap("orcid:m1", "Scrap de teste!")
        assert s is not None
        assert c.scrap_count == 1

    def test_post_scrap_non_member(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        s = c.post_scrap("orcid:nonmember", "Teste")
        assert s is None

    def test_create_evento(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        e = c.create_evento("Banca", "defesa", "2026-06-15", "orcid:f")
        assert e is not None
        assert len(c.eventos) == 1

    def test_get_feed_chronological(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        c.post_scrap("orcid:m1", "Primeiro")
        import time; time.sleep(0.01)
        c.post_scrap("orcid:m1", "Segundo")
        feed = c.get_feed()
        assert feed[0].content == "Segundo"

    def test_moderator_action(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        s = c.post_scrap("orcid:m1", "Conteúdo")
        ok, msg = c.moderator_action("orcid:m1", s.scrap_id, "hide")
        assert ok is True

    def test_vote(self):
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.7)
        ok, weight = c.vote("orcid:m1", "Proposta", True)
        assert ok is True
        assert weight > 0


class TestFeed:

    def test_empty_feed(self):
        f = FeedOrkut()
        assert f.global_feed() == []
        assert f.total_scraps == 0

    def test_global_feed_aggregates(self):
        f = FeedOrkut()
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        c.post_scrap("orcid:m1", "Scrap 1")
        f.register_comunidade(c)
        assert len(f.global_feed()) == 1

    def test_total_pesquisadores(self):
        f = FeedOrkut()
        p = Pesquisador("orcid:test", "Test", "Inst")
        f.register_pesquisador(p)
        assert f.total_pesquisadores == 1

    def test_search_scraps(self):
        f = FeedOrkut()
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        c.post_scrap("orcid:m1", "Luciferase expression results")
        f.register_comunidade(c)
        results = f.search_scraps("luciferase")
        assert len(results) == 1

    def test_scraps_with_latex(self):
        f = FeedOrkut()
        c = Comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m1", 0.6)
        c.post_scrap("orcid:m1", "Sem LaTeX")
        c.post_scrap("orcid:m1", "Com $\\Phi_C$")
        f.register_comunidade(c)
        assert len(f.scraps_with_latex()) == 1


class TestAssistenteAGI:

    def test_initial_state(self):
        agi = AssistenteAGI()
        assert agi.total_interactions == 0

    def test_answer_with_at_gemini(self):
        agi = AssistenteAGI()
        s = Scrap("S-001", "orcid:test", "@Gemini O que é Φ_C?")
        resp = agi.answer_question(s, {"phi_c": 0.65})
        assert resp is not None
        assert "[AGI]" in resp
        assert agi.total_interactions == 1

    def test_answer_without_mention(self):
        agi = AssistenteAGI()
        s = Scrap("S-002", "orcid:test", "Sem menção")
        resp = agi.answer_question(s, {"phi_c": 0.65})
        assert resp is None

    def test_answer_low_phi_c(self):
        agi = AssistenteAGI()
        s = Scrap("S-003", "orcid:test", "@Gemini Pergunta")
        resp = agi.answer_question(s, {"phi_c": 0.5})
        assert resp is None

    def test_suggest_connection(self):
        agi = AssistenteAGI()
        pa = Pesquisador("orcid:a", "A", "Inst")
        pb = Pesquisador("orcid:b", "B", "Inst")
        sug = agi.suggest_connection(pa, pb, "Área similar")
        assert sug["from"] == "orcid:a"
        assert len(sug["seal"]) == 64
        assert agi.total_interactions == 1

    def test_alert_inconsistency(self):
        agi = AssistenteAGI()
        p = Pesquisador("orcid:test", "Test", "Inst")
        s = Scrap("S-001", "orcid:test", "Φ_C=0.58")
        alert = agi.alert_inconsistency(p, s, 0.577, 0.58)
        assert math.isclose(alert["deviation"], 0.003, abs_tol=1e-6)
        assert len(alert["seal"]) == 64


class TestOrkut2:

    def test_create(self):
        o = Orkut2()
        assert o.feed.total_pesquisadores == 0
        assert o.feed.total_comunidades == 0

    def test_register_researcher(self):
        o = Orkut2()
        p = o.register_researcher("orcid:test", "Test", "Inst", "Área")
        assert p.orcid == "orcid:test"
        assert o.feed.total_pesquisadores == 1

    def test_create_comunidade(self):
        o = Orkut2()
        o.register_researcher("orcid:f", "Founder", "Inst")
        c = o.create_comunidade("test-comm", "Test", "Desc", "orcid:f")
        assert c.community_id == "test-comm"
        assert o.feed.total_comunidades == 1

    def test_post_scrap(self):
        o = Orkut2()
        o.register_researcher("orcid:f", "F", "Inst")
        o.register_researcher("orcid:m", "M", "Inst")
        c = o.create_comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m", 0.6)
        s = o.post_scrap("test", "orcid:m", "Scrap de teste")
        assert s is not None
        assert o.feed.total_scraps == 1

    def test_send_depoimento(self):
        o = Orkut2()
        o.register_researcher("orcid:a", "A", "Inst")
        o.register_researcher("orcid:b", "B", "Inst")
        d = o.send_depoimento("orcid:a", "orcid:b", "Excelente!")
        assert d is not None
        assert len(o.depoimentos) == 1

    def test_send_depoimento_unknown(self):
        o = Orkut2()
        o.register_researcher("orcid:a", "A", "Inst")
        d = o.send_depoimento("orcid:a", "orcid:unknown", "Teste")
        assert d is None

    def test_create_evento(self):
        o = Orkut2()
        o.register_researcher("orcid:f", "F", "Inst")
        c = o.create_comunidade("test", "Test", "Desc", "orcid:f")
        e = o.create_evento("test", "Defesa", "defesa", "2026-06-15", "orcid:f")
        assert e is not None

    def test_global_feed(self):
        o = Orkut2()
        o.register_researcher("orcid:f", "F", "Inst")
        o.register_researcher("orcid:m", "M", "Inst")
        c = o.create_comunidade("test", "Test", "Desc", "orcid:f")
        c.add_member("orcid:m", 0.6)
        o.post_scrap("test", "orcid:m", "Primeiro")
        assert len(o.global_feed()) == 1

    def test_canonical_seal(self):
        o = Orkut2()
        seal = o.canonical_seal()
        assert len(seal) == 64

    def test_invariants_present(self):
        o = Orkut2()
        assert math.isclose(o.invariants["ghost"], GHOST)
        assert math.isclose(o.invariants["phi"], PHI)
        assert o.invariants["gap_max"] < 1.0


class TestDemonstration:

    def test_run_returns_keys(self):
        from l_m.orkut_2 import run_demonstration
        r = run_demonstration()
        assert "researchers" in r
        assert "communities" in r
        assert "scraps" in r
        assert "depoimentos" in r
        assert "agi_interactions" in r
        assert "invariants" in r
        assert "canonical_seal" in r

    def test_demo_has_at_least_one_of_each(self):
        from l_m.orkut_2 import run_demonstration
        r = run_demonstration()
        assert r["researchers"] >= 3
        assert r["communities"] >= 2
        assert r["scraps"] >= 3
        assert r["depoimentos"] >= 1
        assert r["agi_interactions"] >= 1
