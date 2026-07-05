"""Tests for Substrate 958 — Clarity Gate."""
import sys
sys.path.insert(0, "substrates/958-clarity-gate")
from clarity_gate import ClarityGate, HeroSection, TERMOS_PROIBIDOS


def test_passa_headline_clara():
    gate = ClarityGate()
    hero = HeroSection(
        headline="Uma plataforma que extrai insights de dados em tempo real",
        subheadline="Para engenheiros que querem deploy em minutos, sem infra",
        cta_text="Começar trial gratuito",
        logos=["Google", "Nubank"],
    )
    report = gate.check(hero)
    assert report.passed


def test_falha_headline_abstrata():
    gate = ClarityGate()
    hero = HeroSection(
        headline="Revolucione sua plataforma definitiva com sinergia next-gen",
        subheadline="Solução integrada para seu ecossistema",
        cta_text="Saiba mais",
    )
    report = gate.check(hero)
    assert not report.passed


def test_pass_headline_simples():
    gate = ClarityGate()
    hero = HeroSection(
        headline="Ferramenta que converte design em código",
        subheadline="Para designers que querem entregar mais rápido",
        cta_text="Testar grátis",
        numbers=["10k+ usuarios"],
    )
    assert gate.check(hero).passed


def test_is_abstract_detecta():
    gate = ClarityGate()
    assert gate._is_abstract("plataforma definitiva para revolucionar")
    assert gate._is_abstract("ecossistema sinérgico powered by AI")
    assert not gate._is_abstract("ferramenta que extrai dados")


def test_comunica_funcao():
    gate = ClarityGate()
    assert gate._comunica_funcao("plataforma que converte audio")
    assert gate._comunica_funcao("ajuda times a colaborar")
    assert not gate._comunica_funcao("Plataforma X")


def test_subheadline_icp():
    gate = ClarityGate()
    assert gate._test_subheadline_icp("Para desenvolvedores")
    assert gate._test_subheadline_icp("Para engenheiros de dados")
    assert not gate._test_subheadline_icp("A melhor solução")


def test_subheadline_resultado():
    gate = ClarityGate()
    assert gate._test_subheadline_resultado("em 5 minutos")
    assert gate._test_subheadline_resultado("sem código")
    assert not gate._test_subheadline_resultado("apenas")


def test_cta_especifico():
    gate = ClarityGate()
    assert gate._test_cta("Começar trial gratuito")
    assert not gate._test_cta("Clique aqui")
    assert not gate._test_cta("Saiba mais")


def test_prova_social():
    gate = ClarityGate()
    hero = HeroSection("x", "y", "cta", logos=["Google"])
    assert gate._test_prova_social(hero)
    hero2 = HeroSection("x", "y", "cta")
    assert not gate._test_prova_social(hero2)


def test_seal():
    gate = ClarityGate()
    hero = HeroSection("Ferramenta que cria sites", "Para criadores", "Testar")
    report = gate.check(hero)
    s = gate.seal(report)
    assert len(s) == 64


def test_termos_proibidos():
    assert "revolucione" in TERMOS_PROIBIDOS
    assert "sinergia" in TERMOS_PROIBIDOS


def test_falha_sem_nada():
    gate = ClarityGate()
    hero = HeroSection("", "", "")
    assert not gate.check(hero).passed
