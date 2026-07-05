"""Tests for Substrate 960 — Polynomial Arkhe."""
import sys
sys.path.insert(0, "substrates/960-arkhe-stack")
import numpy as np
from polynomial_arkhe import PolynomialArkhe, build_canonical_polynomial


def test_arkhe_small():
    A = np.array([[1.0, 0.0], [0.0, 2.0]])
    pa = PolynomialArkhe(A, [1, 2])
    assert abs(pa.Arkhe(1) - 1.0) < 0.01
    assert abs(pa.Arkhe(2) - 2.0) < 0.01


def test_arkhe_raises():
    A = np.array([[1.0]])
    pa = PolynomialArkhe(A, [1])
    try:
        pa.Arkhe(999)
        assert False
    except ValueError:
        assert True


def test_canonical_build():
    pa = build_canonical_polynomial(max_substrate=10)
    assert pa.N == 10
    assert abs(pa.Arkhe(1) - 1.0) < 10.0


def test_spectral_gap():
    A = np.array([[1.0, 0.0], [0.0, 5.0]])
    pa = PolynomialArkhe(A, [1, 2])
    assert pa.spectral_gap() > 0.0


def test_t_duality():
    A = np.array([[1.0, 0.0], [0.0, 2.0]])
    pa = PolynomialArkhe(A, [1, 2])
    assert pa.t_duality_pair(1) == 2
    assert pa.t_duality_pair(2) == 1


def test_factored_form():
    A = np.array([[1.0, 0.0], [0.0, 2.0]])
    pa = PolynomialArkhe(A, [1, 2])
    form = pa.factored_form(limit=2)
    assert "(x - 1.0" in form or "(x - 2.0" in form


def test_polynomial_equation():
    A = np.array([[1.0, 0.0], [0.0, 2.0]])
    pa = PolynomialArkhe(A, [1, 2])
    eq = pa.polynomial_equation()
    assert "=" in eq


def test_substrate_mode():
    A = np.array([[1.0, 0.0], [0.0, 2.0]])
    pa = PolynomialArkhe(A, [1, 2])
    mode = pa.substrate_mode(1)
    assert mode["substrate_id"] == 1
    assert "eigenvalue" in mode


def test_axiarchy_stability():
    A = np.array([[2.0, 0.0], [0.0, 3.0]])
    pa = PolynomialArkhe(A, [1, 2])
    assert pa.verify_axiarchy_stability({1: 0.9, 2: 0.8})
    assert not pa.verify_axiarchy_stability({1: 0.9, 2: 0.3})


def test_canonical_build_large():
    pa = build_canonical_polynomial(max_substrate=960, cross_link_density=0.001)
    assert pa.N == 960
    assert len(pa.eigenvalues) == 960
