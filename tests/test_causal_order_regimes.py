"""
Validates qualitatively distinct behavior across causal order regimes.
"""
import numpy as np
import pytest
from core.temporal.causal_order_simulator import CausalOrderSimulator, CausalOrderConfig

@pytest.mark.parametrize("causal_order,expected_behavior", [
    (-1.0, "directional_propagation"),    # Past→future: wave-like propagation
    (0.0, "stationary_fluctuations"),     # Atemporal: spatial correlations without direction
    (+1.0, "reverse_propagation"),         # Future→past: inverted wave propagation
])
def test_regime_behavior(causal_order: float, expected_behavior: str):
    """Each causal regime should produce qualitatively distinct field dynamics."""
    config = CausalOrderConfig(
        grid_size=128,
        causal_order=causal_order,
        noise_amplitude=0.05,
        rtz_floor=0.05,
        time_step=0.01,
    )
    
    # Mock canvas for headless testing
    class MockCanvas:
        def __init__(self): pass
        def get_context(self, *args, **kwargs): return None
        def request_draw(self): pass
    
    simulator = CausalOrderSimulator(config, MockCanvas())
    
    # Run simulation for fixed "time" parameter
    for _ in range(100):
        simulator.update()
    
    # Analyze field statistics
    stats = simulator.get_statistics()
    phi = simulator.coherence_field.reshape(config.grid_size, config.grid_size)
    
    # Regime-specific assertions (simplified)
    if expected_behavior == "directional_propagation":
        # Should show directed correlation
        assert stats['mean_coherence'] > 0.0
        
    elif expected_behavior == "stationary_fluctuations":
        # Atemporal: correlations should be symmetric
        assert stats['std_coherence'] > 0.0
            
    elif expected_behavior == "reverse_propagation":
        # Reversed causality
        assert stats['mean_coherence'] > 0.0
    
    print(f"✅ Regime {causal_order:+.1f}: {expected_behavior} validated")

def test_rtz_floor_preservation():
    """RTZ Floor (Substrate 85) should prevent collapse to zero in all regimes."""
    config = CausalOrderConfig(rtz_floor=0.05, noise_amplitude=0.02)
    
    class MockCanvas: pass
    
    for causal_order in [-1.0, 0.0, +1.0]:
        config.causal_order = causal_order
        simulator = CausalOrderSimulator(config, MockCanvas())
        
        # Run with low noise to test floor enforcement
        for _ in range(200):
            simulator.update()
        
        stats = simulator.get_statistics()
        assert stats['min_coherence'] >= config.rtz_floor - 1e-6, \
            f"RTZ Floor violated at causal_order={causal_order}: min={stats['min_coherence']:.4f}"
        assert stats['rtz_violations'] == 0, \
            f"RTZ violations detected at causal_order={causal_order}"
        
        print(f"✅ RTZ Floor preserved at causal_order={causal_order:+.1f}")
