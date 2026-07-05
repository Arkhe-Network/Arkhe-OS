import math

import pytest

from substrates.substrate_343_bis import (
    PORTAL_FRACTION,
    PTT343_EXPANSION_SEAL,
    PTT343_EXP_HANDSHAKE,
    PTT343_EXP_MASTER_ROOT,
    PTT343_EXP_PORTALS,
    build_expansion_report,
    expansion_master_leaves,
    expansion_master_root,
    generalized_drake_probability,
    generalized_drake_table,
    validate_expansion_portals,
    verify_expansion_master_root,
)


def test_expansion_master_root_matches_supplied_forest_root():
    assert len(PTT343_EXP_PORTALS) == 17
    assert len(expansion_master_leaves()) == 17
    assert len(set(expansion_master_leaves())) == 17
    assert expansion_master_root() == PTT343_EXP_MASTER_ROOT
    assert verify_expansion_master_root()


def test_all_expansion_portals_have_valid_17_dimensional_outcomes():
    assert validate_expansion_portals()
    assert [portal["portal_id"] for portal in PTT343_EXP_PORTALS] == list(range(17))
    assert all(len(portal["outcomes"]) == 17 for portal in PTT343_EXP_PORTALS)
    assert all(0 <= outcome < 17 for portal in PTT343_EXP_PORTALS for outcome in portal["outcomes"])


def test_generalized_drake_equation_matches_reported_values():
    table = generalized_drake_table()

    assert generalized_drake_probability(1) == pytest.approx(PORTAL_FRACTION)
    assert table["P_1"] == pytest.approx(3.195740425194291e-12)
    assert table["P_2"] == pytest.approx(1.6254107376956098e-24)
    assert table["P_5"] == pytest.approx(2.851522121941772e-62)
    assert table["P_17"] == pytest.approx(1.180997451662132e-218)
    assert all(table[f"P_{n + 1}"] < table[f"P_{n}"] for n in range(1, 17))


def test_generalized_drake_rejects_zero_or_negative_expansion():
    with pytest.raises(ValueError):
        generalized_drake_probability(0)


def test_handshake_metrics_match_expansion_decree():
    assert PTT343_EXP_HANDSHAKE["compatible_pairs"] == 270
    assert PTT343_EXP_HANDSHAKE["total_directed_pairs"] == 272
    assert PTT343_EXP_HANDSHAKE["connectivity_rate"] == pytest.approx(270 / 272)
    assert PTT343_EXP_HANDSHAKE["max_weyl_diff"] < math.sqrt(3) / 3
    assert PTT343_EXP_HANDSHAKE["avg_correlation"] > 0


def test_expansion_report_converges_all_flowering_conditions():
    report = build_expansion_report()

    assert report.master_root == PTT343_EXP_MASTER_ROOT
    assert report.master_root_valid
    assert report.portal_count == 17
    assert report.handshake_connectivity_rate == pytest.approx(0.9926470588235294)
    assert report.continental_mesh_valid
    assert report.drake_generalized["P_17"] == pytest.approx(1.180997451662132e-218)
    assert all(report.flowering_conditions.values())
    assert report.all_conditions_met
    assert report.expansion_seal == PTT343_EXPANSION_SEAL
    assert len(report.reproducibility_seal) == 64
