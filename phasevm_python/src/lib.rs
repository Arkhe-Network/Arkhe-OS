# phasevm_python/src/lib.rs — Python FFI bindings for PhaseVM via PyO3 (Updated with warm-up cache)

use pyo3::prelude::*;
use pyo3::types::PyList;
use phasevm::{PhaseVM, default_warmup_circuits, PhaseVMError};
use num_complex::Complex64;

/// Python wrapper for PhaseVM JIT compiler
#[pyclass]
struct PyPhaseVM {
    vm: PhaseVM,
}

#[pymethods]
impl PyPhaseVM {
    #[new]
    fn new() -> PyResult<Self> {
        let vm = PhaseVM::new()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        Ok(PyPhaseVM { vm })
    }
    
    /// Compile a circuit (list of gate names) and return Jones invariant as (real, imag)
    #[pyo3(signature = (gates))]
    fn compile_circuit(&mut self, gates: &PyList) -> PyResult<(f64, f64)> {
        // Convert Python list to Rust Vec<String>
        let gate_vec: Vec<String> = gates
            .iter()
            .map(|item| item.extract::<String>())
            .collect::<Result<_, _>>()
            .map_err(|e| pyo3::exceptions::PyTypeError::new_err(e.to_string()))?;
        
        // Compile via PhaseVM
        let result = self.vm.compile_circuit(&gate_vec)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        
        // Return as tuple (real, imag)
        Ok((result.re, result.im))
    }
    
    /// Warm-up cache by pre-compiling frequent circuits during initialization
    #[pyo3(signature = (circuits = None))]
    fn warmup_cache(&mut self, circuits: Option<&PyList>) -> PyResult<(usize, f64)> {
        let warmup_circuits: Vec<Vec<String>> = if let Some(py_circuits) = circuits {
            py_circuits
                .iter()
                .map(|item| {
                    item.extract::<&PyList>()
                        .map(|list| {
                            list.iter()
                                .map(|g| g.extract::<String>())
                                .collect::<Result<Vec<_>, _>>()
                        })
                        .unwrap_or_else(|_| Ok(Vec::new()))
                })
                .collect::<Result<_, _>>()
                .map_err(|e| pyo3::exceptions::PyTypeError::new_err(e.to_string()))?
        } else {
            default_warmup_circuits()
        };
        
        let (hits, elapsed) = self.vm.warmup_cache(&warmup_circuits);
        Ok((hits, elapsed))
    }
    
    /// Clear the JIT compilation cache
    fn clear_cache(&mut self) {
        self.vm.cache.clear();
        self.vm.circuit_cache.clear();
    }
    
    /// Get cache statistics (bytecode_cache_size, circuit_cache_size)
    fn cache_stats(&self) -> PyResult<(usize, usize)> {
        Ok((self.vm.cache.len(), self.vm.circuit_cache.len()))
    }
    
    /// Get performance statistics (avg_ms, p99_ms, max_ms)
    fn perf_stats(&self) -> PyResult<(f64, f64, f64)> {
        Ok(self.vm.perf_stats())
    }
}

/// Module initialization function for PyO3
#[pymodule]
fn phasevm_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<PyPhaseVM>()?;
    Ok(())
}
