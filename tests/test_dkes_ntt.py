import pytest
import numpy as np
import pytest as _pt; _pt.importorskip("torch")  # dep pesada opcional
import torch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dkes_ntt_arkhe_rtl_100t import (
    NTTEngine, RKHSKernel, MKELDualSolver, DKES_NTT,
    ARKHE_RTL_Wrapper, ModelBridge100T
)

DIM = 64

# --- NTT ---
def test_ntt_multiply_identity():
    ntt = NTTEngine(n=64)
    a = np.random.randn(64)
    impulse = np.zeros(64)
    impulse[0] = 1.0
    c = ntt.multiply(a, impulse)
    assert c.shape == (64,)
    assert np.allclose(c, a, atol=1e-5)



def test_ntt_batch_inner():
    ntt = NTTEngine(n=32)
    X = np.random.randn(4, 16)
    Y = np.random.randn(3, 16)
    result = ntt.batch_inner_products(X, Y)
    assert result.shape == (4, 3)
    expected = X @ Y.T
    assert np.allclose(result, expected, atol=1e-5)

def test_ntt_batch_inner_large():
    ntt = NTTEngine(n=64)
    X = np.random.randn(3, 512)
    Y = np.random.randn(2, 512)
    result = ntt.batch_inner_products(X, Y)
    expected = X @ Y.T
    assert np.allclose(result, expected, atol=1e-4)

# --- KERNEL ---
def test_kernel_rbf():
    k = RKHSKernel(kernel_type='rbf', gamma=1.0)
    x1 = torch.randn(4, DIM)
    x2 = torch.randn(3, DIM)
    out = k(x1, x2)
    assert out.shape == (4, 3)
    assert out.min() >= 0.0
    assert out.max() <= 1.0

def test_kernel_polynomial():
    k = RKHSKernel(kernel_type='polynomial', gamma=0.1, degree=3)
    x1 = torch.randn(4, DIM)
    x2 = torch.randn(3, DIM)
    out = k(x1, x2)
    assert out.shape == (4, 3)

def test_kernel_linear():
    k = RKHSKernel(kernel_type='linear')
    x1 = torch.randn(4, DIM)
    x2 = torch.randn(3, DIM)
    out = k(x1, x2)
    assert out.shape == (4, 3)

# --- DUAL SOLVER ---
def test_dual_solver():
    solver = MKELDualSolver(C=100.0, max_iter=10, lr=0.1)
    N = 16
    K_stack = torch.stack([torch.randn(N, N) ** 2 for _ in range(3)])
    K_stack = K_stack / K_stack.max()
    y = 2.0 * (torch.rand(N) > 0.5).float() - 1.0
    w = torch.ones(3) / 3
    beta, alphas = solver(K_stack, y, w)
    assert beta.shape == (N,)
    assert beta.min() >= 0.0
    assert len(alphas) == 3

# --- DKES_NTT ---
def test_dkes_init():
    dkes = DKES_NTT(dim=DIM, num_experts=6, num_prototypes=32)
    assert dkes.dim == DIM
    assert dkes.num_experts == 6
    assert len(dkes.kernels) == 6

def test_dkes_forward():
    dkes = DKES_NTT(dim=DIM, num_experts=6, num_prototypes=32)
    query = torch.randn(2, DIM)
    score, info = dkes(query)
    assert score.shape == (2,)
    assert 'beta' in info
    assert 'w' in info
    assert 'theosis_diversity' in info
    assert info['w'].shape == (6,)

def test_dkes_forward_custom_data():
    dkes = DKES_NTT(dim=DIM, num_experts=6, num_prototypes=0, use_ntt=False)
    prototypes = torch.randn(16, DIM)
    labels = 2.0 * (torch.rand(16) > 0.5).float() - 1.0
    query = torch.randn(1, DIM)
    score, info = dkes(query, prototype_override=prototypes, labels_override=labels)
    assert score.shape == (1,)

def test_dkes_diversity():
    dkes = DKES_NTT(dim=DIM, num_experts=6, num_prototypes=16)
    K = torch.randn(6, 16, 16)
    K = K @ K.transpose(1, 2)
    w = torch.ones(6) / 6
    div = dkes._compute_diversity(K, w)
    assert div >= 0.0

# --- ARKHE-RTL ---
def test_rtl_init():
    dkes = DKES_NTT(dim=DIM, num_experts=4, num_prototypes=16)
    rtl = ARKHE_RTL_Wrapper(dkes, bit_width=16, fractional_bits=8)
    assert rtl.bit_width == 16

def test_rtl_quantize():
    dkes = DKES_NTT(dim=DIM, num_experts=4, num_prototypes=8, use_ntt=False)
    rtl = ARKHE_RTL_Wrapper(dkes, bit_width=8, fractional_bits=4)
    prototypes = torch.randn(8, DIM)
    labels = 2.0 * (torch.rand(8) > 0.5).float() - 1.0
    dkes.prototypes = prototypes
    dkes.prototype_labels = labels
    query = torch.randn(1, DIM)
    score, info = rtl(query)
    assert score.shape == (1,)

# --- 100T BRIDGE ---
def test_bridge_init():
    dkes = DKES_NTT(dim=DIM, num_experts=4, num_prototypes=8)
    bridge = ModelBridge100T('deepseek-v4-pro', dkes)
    assert bridge.model_name == 'deepseek-v4-pro'
    assert bridge.config['params'] == 1.6e12

def test_bridge_forward():
    dkes = DKES_NTT(dim=DIM, num_experts=4, num_prototypes=8, use_ntt=False)
    bridge = ModelBridge100T('deepseek-v4-pro', dkes)
    hidden = torch.randn(1, 2, 8192)
    results = bridge.forward(hidden)
    assert len(results) == 2

def test_bridge_unknown_model():
    dkes = DKES_NTT(dim=DIM, num_experts=4, num_prototypes=8)
    bridge = ModelBridge100T('unknown-model', dkes)
    assert bridge.config['dim'] == 2048
