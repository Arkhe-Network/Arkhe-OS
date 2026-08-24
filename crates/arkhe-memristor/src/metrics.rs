//! Métricas de consumo, endurance e retenção.

/// Métricas de potência.
#[derive(Debug, Clone, Copy)]
pub struct PowerMetrics {
    /// Consumo de potência na operação SET (em mW)
    pub set_power_mw: f64,
    /// Consumo de potência na operação RESET (em mW)
    pub reset_power_mw: f64,
    /// Potência média (em mW)
    pub average_power_mw: f64,
    /// Potência de pico (em mW)
    pub peak_power_mw: f64,
}

/// Métricas de endurance.
#[derive(Debug, Clone, Copy)]
pub struct EnduranceMetrics {
    /// Total de ciclos realizados
    pub total_cycles: u32,
    /// Ciclos restantes estimados
    pub remaining_cycles: u32,
    /// Vida útil estimada em ciclos
    pub estimated_lifetime_cycles: u32,
    /// Tempo de retenção em segundos
    pub retention_secs: f64,
}

/// Trait para fornecer métricas.
pub trait Metrics {
    /// Retorna as métricas de potência.
    fn power_metrics(&self) -> PowerMetrics;
    /// Retorna as métricas de endurance.
    fn endurance_metrics(&self) -> EnduranceMetrics;
}
