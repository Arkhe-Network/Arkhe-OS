//! Parâmetros para operações SET e RESET.

/// Parâmetros para a operação SET.
#[derive(Debug, Clone, Copy)]
pub struct SetParams {
    /// Tensão a ser aplicada (deve ser < 0.1 V)
    pub voltage: f64,
    /// Duração do pulso em ms (padrão: 150 ms)
    pub pulse_duration_ms: u64,
}

impl Default for SetParams {
    fn default() -> Self {
        Self {
            voltage: 0.10,
            pulse_duration_ms: 150,
        }
    }
}

/// Parâmetros para a operação RESET.
#[derive(Debug, Clone, Copy)]
pub struct ResetParams {
    /// Tensão a ser aplicada (deve ser < 0.1 V, valor positivo)
    pub voltage: f64,
    /// Duração do pulso em ms (padrão: 200 ms)
    pub pulse_duration_ms: u64,
}

impl Default for ResetParams {
    fn default() -> Self {
        Self {
            voltage: 0.08,
            pulse_duration_ms: 200,
        }
    }
}
