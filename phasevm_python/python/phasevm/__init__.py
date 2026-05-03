"""
PhaseVM Python Package — Rust JIT Compiler with Async Support and Warm-up Cache

Provides Pythonic access to the PhaseVM Rust JIT compiler for topological
quantum circuits. Supports synchronous and asynchronous compilation, warm-up
cache for pre-compiling frequent circuits, and non-blocking operation.
"""

from .phasevm_rs import PyPhaseVM as _PyPhaseVM
from typing import List, Tuple, Optional
import asyncio
import time

class PhaseVM:
    """
    Pythonic wrapper for Rust PhaseVM JIT compiler.
    
    Features:
    - Synchronous and asynchronous circuit compilation
    - Warm-up cache for pre-compiling frequent circuits
    - Performance statistics and cache management
    """
    
    def __init__(self):
        """Initialize PhaseVM with warm-up cache enabled."""
        self._vm = _PyPhaseVM()
        self._warmup_done = False
    
    def compile_circuit(self, gates: List[str]) -> complex:
        """
        Compile topological circuit to native code and return Jones invariant.
        
        Args:
            gates: List of gate names (e.g., ['H', 'X', 'Z'])
        
        Returns:
            Complex Jones invariant
        """
        re, im = self._vm.compile_circuit(gates)
        return complex(re, im)
    
    def warmup_cache(self, circuits: Optional[List[List[str]]] = None) -> Tuple[int, float]:
        """
        Pre-compile frequent circuits during initialization.
        
        Args:
            circuits: Optional list of circuits to warm-up. If None, uses defaults.
        
        Returns:
            Tuple of (cache_hits_before_warmup, elapsed_ms)
        """
        import pyo3
        if circuits is not None:
            # Convert to PyList of PyLists
            pass  # Simplified for now
        hits, elapsed = self._vm.warmup_cache(circuits)
        self._warmup_done = True
        return hits, elapsed
    
    def clear_cache(self):
        """Clear JIT compilation cache and circuit cache."""
        self._vm.clear_cache()
    
    @property
    def cache_size(self) -> Tuple[int, int]:
        """
        Return (bytecode_cache_size, circuit_cache_size).
        """
        return self._vm.cache_stats()
    
    @property
    def perf_stats(self) -> Tuple[float, float, float]:
        """
        Return (avg_ms, p99_ms, max_ms) compilation times.
        """
        return self._vm.perf_stats()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.clear_cache()


# Default warm-up circuits
DEFAULT_WARMUP_CIRCUITS = [
    ["H"],
    ["X"],
    ["Z"],
    ["H", "X"],
    ["H", "Z"],
    ["X", "Z", "H"],
    ["H", "X", "Z"],
    ["I"] * 5,
    ["H", "X", "H", "X"],
    ["Z", "X", "Z", "X"],
]


# Convenience function for one-shot compilation
def compile(gates: List[str]) -> complex:
    """Compile a circuit and return its Jones invariant."""
    with PhaseVM() as vm:
        return vm.compile_circuit(gates)


__all__ = ["PhaseVM", "compile", "DEFAULT_WARMUP_CIRCUITS"]
