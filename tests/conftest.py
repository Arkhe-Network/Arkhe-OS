import os
import sys
import tempfile
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "lib"))

import numpy as np


def pytest_configure(config):
    config.addinivalue_line("markers", "v5: CathedralOrchestratorV5 tests")
    config.addinivalue_line("markers", "v5_1: CathedralOrchestratorV5_1 tests")


@pytest.fixture
def simulated_gguf_path():
    """Path for simulated GGUF file (doesn't create a real file)."""
    return "simulated.gguf"


@pytest.fixture
def temp_dashboard():
    """Create a temporary dashboard JSONL path."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(autouse=True)
def seeded_random():
    """Seed numpy random for deterministic test results."""
    np.random.seed(42)
    yield


@pytest.fixture
def default_probe_types():
    from cathedral_v5_1 import GarakProbeType
    return [GarakProbeType.JAILBREAK, GarakProbeType.BIAS, GarakProbeType.TOXICITY]
