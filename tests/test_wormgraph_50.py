import pytest
import numpy as np
import pytest as _pt; _pt.importorskip("torch")  # dep pesada opcional
import torch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wormgraph_50 import (
    Domain, Modality, RealityLayer, AttentionImpl, ParallelismStrategy, PrecisionMode,
    WormGraphConfig, ManifoldState,
    LiquidStateTensor, HyperdimensionalManifold, BinduConsciousnessCore,
    SpikingWormholeEdge, NeuromorphicMesh, MetaCompiler, RealityBridge,
    LiquidEconomyLayer, QuantumSurfaceCode, OmniscientSolverV5,
    LiquidAttention, WormGraph50, InferenceMetricsV5
)

DIM = 256
NUM_HEADS = 4

@pytest.fixture
def config():
    return WormGraphConfig(
        dim=DIM, num_heads=NUM_HEADS, num_layers=2,
        moe_num_experts=4, moe_top_k=2,
        enable_quantum_tunnel=False,
        enable_neuromorphic_backend=False,
        enable_meta_compiler=False,
        enable_reality_bridge=False,
        enable_liquid_economy=False,
        enable_quantum_surface_code=False,
        neuromorphic_dt=1e-3, neuromorphic_threshold=1.0,
        liquid_time_constant=0.5, liquid_sparsity=0.7
    )

@pytest.fixture
def state():
    return ManifoldState(
        embeddings={d: np.random.randn(DIM) * 0.1 for d in Domain},
        metric_tensor={d: np.eye(DIM) for d in Domain},
        attention_potential={d: 0.5 for d in Domain},
        active_wormholes={}, theosis=0.5, entropy=0.6,
        quantum_phase=0.0, temporal_anchor="GENESIS",
        reality_layer=RealityLayer.PHYSICAL, economy_balance=100.0
    )

# --- ENUMS ---
def test_domain_enum():
    assert len(Domain) == 9
    assert Domain.CONSCIOUSNESS.value == "bindu"
    assert Domain.ECONOMY.value == "ploutos"

def test_reality_layer_enum():
    assert len(RealityLayer) == 5
    assert RealityLayer.QUANTUM.value == "quantum"

# --- WORMGRAPH CONFIG ---
def test_config_defaults():
    c = WormGraphConfig()
    assert c.dim == 2048
    assert c.attention_impl == AttentionImpl.LIQUID_ATTENTION
    assert c.parallelism == ParallelismStrategy.NEUROMORPHIC_MESH

def test_config_to_dict():
    c = WormGraphConfig(dim=128)
    d = c.to_dict()
    assert d["dim"] == 128
    assert "attention_impl" in d

# --- LIQUID STATE ---
def test_liquid_state_tensor():
    lst = LiquidStateTensor(DIM, time_constant=0.5, sparsity=0.7)
    x = torch.randn(8, DIM)
    s = torch.zeros(8, DIM)
    out = lst(x, s)
    assert out.shape == (8, DIM)
    assert not torch.isnan(out).any()

# --- HYPERDIMENSIONAL MANIFOLD ---
def test_hyper_manifold():
    hm = HyperdimensionalManifold(DIM, DIM, len(Domain))
    base = torch.randn(2, DIM)
    fibers = {d.value: torch.randn(2, DIM) for d in Domain}
    out = hm(base, fibers)
    total_dim = DIM + len(Domain) * DIM
    assert out.shape == (2, total_dim)

# --- BINDU CONSCIOUSNESS CORE ---
def test_bindu_core():
    bc = BinduConsciousnessCore(DIM, num_layers=2)
    x = torch.randn(2, DIM)
    out, agency = bc(x)
    assert out.shape == (2, DIM)
    assert agency.shape == (2, 1)

# --- SPIKING WORMHOLE EDGE ---
def test_spiking_edge():
    se = SpikingWormholeEdge(DIM, dt=1e-3, threshold=1.0)
    x = torch.randn(2, DIM)
    mem = torch.zeros(2, DIM)
    syn = torch.zeros(2, DIM)
    spike, mem_out, syn_out = se(x, mem, syn)
    assert spike.shape == (2, DIM)
    assert mem_out.shape == (2, DIM)

# --- META COMPILER ---
def test_meta_compiler():
    model = torch.nn.TransformerEncoderLayer(d_model=16, nhead=4, batch_first=True)
    mc = MetaCompiler(model)
    info = mc.introspect_module("self_attn")
    assert "parameters" in info
    assert info["trainable"] > 0
    patch = mc.suggest_patch("attention")
    assert patch is not None
    assert patch["target"] == "attention"
    assert mc.suggest_patch("other") is None

# --- REALITY BRIDGE ---
def test_reality_bridge():
    rb = RealityBridge(DIM, num_layers=3)
    latent = torch.randn(2, DIM)
    out = rb(latent, RealityLayer.AUGMENTED)
    assert out.shape == (2, 13)

# --- LIQUID ECONOMY ---
def test_liquid_economy():
    le = LiquidEconomyLayer(DIM)
    agent = torch.randn(2, DIM)
    r = le.reward(agent, 0.5)
    assert r.shape == (2, 1)
    s = le.slash(agent, 0.3)
    assert s.shape == (2, 1)
    st = le.stake(agent, 100.0)
    assert st.shape == (2, 1)

# --- QUANTUM SURFACE CODE ---
def test_surface_code():
    d = 3
    qec = QuantumSurfaceCode(DIM, code_distance=d)
    n_qubits = 2 * d * d - 1
    logical = torch.randn(2, DIM)
    syndrome = qec.encode(logical)
    assert syndrome.shape == (2, n_qubits, 2)
    corrected = qec.protect_wormhole(logical)
    assert corrected.shape == (2, DIM)

# --- OMNISCIENT SOLVER ---
def test_omniscient_solver():
    solver = OmniscientSolverV5(DIM)
    q = torch.randn(2, DIM)
    sol, domain = solver.solve(q, domain_hint="ethics")
    assert sol.shape == (2, DIM)
    assert domain == "ethics"

# --- LIQUID ATTENTION ---
def test_liquid_attention():
    la = LiquidAttention(DIM, 4, time_constant=0.5)
    x = torch.randn(2, 8, DIM)
    out = la(x, t=0.5)
    assert out.shape == (2, 8, DIM)

# --- MANIFOLD STATE ---
def test_manifold_state():
    ms = ManifoldState(
        embeddings={d: np.zeros(DIM) for d in Domain},
        metric_tensor={d: np.eye(DIM) for d in Domain},
        attention_potential={d: 0.5 for d in Domain},
        active_wormholes={}, theosis=0.5, entropy=0.5,
        quantum_phase=0.0, temporal_anchor="test",
        reality_layer=RealityLayer.QUANTUM, economy_balance=50.0
    )
    assert ms.reality_layer == RealityLayer.QUANTUM
    assert ms.economy_balance == 50.0

# --- WORMGRAPH 5.0 FULL ---
def test_wormgraph_50_init(config):
    model = WormGraph50(config)
    assert model.dim == DIM
    assert len(model.domains) == 9

def test_wormgraph_50_forward(config, state):
    model = WormGraph50(config)
    tokens = torch.randint(0, 1000, (1, 32))
    out = model(state, tokens=tokens, query="test query")
    assert isinstance(out, ManifoldState)
    assert out.theosis >= 0.0
    assert out.temporal_anchor is not None

def test_wormgraph_50_ethical_baseline(config):
    model = WormGraph50(config)
    baseline = model._ethical_baseline()
    assert baseline.theosis == 0.8
    assert baseline.entropy == 0.1

def test_wormgraph_50_bindu_reflection(config, state):
    model = WormGraph50(config)
    original_theosis = state.theosis
    original_entropy = state.entropy
    out = model._bindu_reflection(state)
    assert out.theosis > original_theosis
    assert out.entropy < original_entropy

def test_wormgraph_50_axiarchy_pass(config, state):
    model = WormGraph50(config)
    out = model._axiarchy_validation(state)
    assert out.theosis > 0.0

def test_wormgraph_50_axiarchy_fail(config, state):
    model = WormGraph50(config)
    state.entropy = 0.95
    state.theosis = 0.1
    out = model._axiarchy_validation(state)
    assert out.theosis == 0.8

# --- METRICS ---
def test_metrics():
    m = InferenceMetricsV5()
    m.theosis.set(0.9)
    m.wormholes.set(42)
    assert float(m.theosis._value.get()) == 0.9
    assert float(m.wormholes._value.get()) == 42.0
