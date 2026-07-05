"""Tests for Substrate 960 — ARKHE-STACK."""
import sys
sys.path.insert(0, "substrates/960-arkhe-stack")
from arkhe_stack import ARKHEStack, Layer


def test_all_layers_present():
    s = ARKHEStack()
    for layer in Layer:
        assert layer in s.layers


def test_eight_layers():
    s = ARKHEStack()
    assert len(s.layers) == 8


def test_canon_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.CANON].substrates) >= 3


def test_hardware_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.HARDWARE].substrates) >= 1


def test_runtime_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.RUNTIME].substrates) >= 1


def test_crypto_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.CRYPTO].substrates) >= 3


def test_network_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.NETWORK].substrates) >= 3


def test_compute_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.COMPUTE].substrates) >= 3


def test_ontology_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.ONTOLOGY].substrates) >= 1


def test_application_has_substrates():
    s = ARKHEStack()
    assert len(s.layers[Layer.APPLICATION].substrates) >= 3


def test_list_substrates():
    s = ARKHEStack()
    all_subs = s.list_substrates()
    assert len(all_subs) >= 20


def test_data_flow():
    s = ARKHEStack()
    flow = s.trace_data_flow()
    assert len(flow) == 8


def test_stack_integrity():
    s = ARKHEStack()
    integrity = s.verify_stack_integrity()
    assert all(v["connected"] for v in integrity.values())


def test_get_layer():
    s = ARKHEStack()
    layer = s.get_layer(Layer.CANON)
    assert layer.name == "O Cânone Constitucional"
