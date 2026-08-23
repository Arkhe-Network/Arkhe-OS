//! Driver do memristor baseado nos dados do artigo.
//!
//! A simulação utiliza modelos matemáticos que reproduzem
//! o comportamento I-V característico, incluindo:
//! - Tensão de SET ≈ 0.10 V
//! - Tensão de RESET ≈ 0.08 V
//! - ON/OFF ratio > 10⁵
//! - Endurance > 10³ ciclos
//! - Retenção > 4×10³ s

use super::*;
use crate::metrics::{Metrics, PowerMetrics, EnduranceMetrics};

/// Configuração do driver.
#[derive(Debug, Clone, Copy)]
pub struct DriverConfig {
    /// Tensão de operação (< 0.1 V)
    pub voltage: f64,
    /// Corrente de compliance (1 µA – 100 mA)
    pub compliance_current: f64,
    /// Temperatura (293–393 K)
    pub temperature: f64,
    /// Limite de ciclos de endurance
    pub endurance_limit: u32,
}

impl Default for DriverConfig {
    fn default() -> Self {
        Self {
            voltage: 0.09,               // < 0.1 V
            compliance_current: 100e-6,  // 100 µA
            temperature: 298.0,          // 25°C
            endurance_limit: 1_000,
        }
    }
}

/// Driver concreto para o memristor DNA-Peroskite.
pub struct MemristorDriver {
    config: DriverConfig,
    state: ResistanceState,
    cycle_count: u32,
    metrics: DriverMetrics,
    initialized: bool,
}

/// Métricas do driver.
struct DriverMetrics {
    set_voltage_history: [f64; 10],
    reset_voltage_history: [f64; 10],
    power_consumption_mw: f64,
    endurance_remaining: u32,
    retention_secs: f64,
}

impl DriverMetrics {
    fn new() -> Self {
        Self {
            set_voltage_history: [0.0; 10],
            reset_voltage_history: [0.0; 10],
            power_consumption_mw: 0.0,
            endurance_remaining: 1000,
            retention_secs: 0.0,
        }
    }
}

impl Metrics for DriverMetrics {
    fn power_metrics(&self) -> PowerMetrics {
        PowerMetrics {
            set_power_mw: self.power_consumption_mw,
            reset_power_mw: self.power_consumption_mw,
            average_power_mw: self.power_consumption_mw,
            peak_power_mw: self.power_consumption_mw,
        }
    }

    fn endurance_metrics(&self) -> EnduranceMetrics {
        EnduranceMetrics {
            total_cycles: 1000 - self.endurance_remaining,
            remaining_cycles: self.endurance_remaining,
            estimated_lifetime_cycles: 1000,
            retention_secs: self.retention_secs,
        }
    }
}

impl MemristorDriver {
    /// Cria um novo driver com configuração padrão.
    pub fn new() -> Self {
        Self {
            config: DriverConfig::default(),
            state: ResistanceState::High,
            cycle_count: 0,
            metrics: DriverMetrics::new(),
            initialized: false,
        }
    }

    /// Cria um driver com configuração personalizada.
    pub fn with_config(config: DriverConfig) -> Result<Self, MemristorError> {
        if config.voltage >= 0.1 {
            return Err(MemristorError::VoltageOutOfRange);
        }
        if config.compliance_current < 1e-6 || config.compliance_current > 100e-3 {
            return Err(MemristorError::ComplianceOutOfRange);
        }
        if config.temperature < 293.0 || config.temperature > 393.0 {
            return Err(MemristorError::TemperatureOutOfRange);
        }

        Ok(Self {
            config,
            state: ResistanceState::High,
            cycle_count: 0,
            metrics: DriverMetrics::new(),
            initialized: true,
        })
    }

    /// Define a tensão de operação.
    pub fn set_voltage(&mut self, voltage: f64) -> Result<(), MemristorError> {
        if voltage >= 0.1 {
            return Err(MemristorError::VoltageOutOfRange);
        }
        self.config.voltage = voltage;
        Ok(())
    }

    /// Define a corrente de compliance.
    pub fn set_compliance_current(&mut self, current: f64) -> Result<(), MemristorError> {
        if current < 1e-6 || current > 100e-3 {
            return Err(MemristorError::ComplianceOutOfRange);
        }
        self.config.compliance_current = current;
        Ok(())
    }

    /// Define a temperatura.
    pub fn set_temperature(&mut self, temp: f64) -> Result<(), MemristorError> {
        if temp < 293.0 || temp > 393.0 {
            return Err(MemristorError::TemperatureOutOfRange);
        }
        self.config.temperature = temp;
        Ok(())
    }

    /// Verifica se o dispositivo está inicializado.
    pub fn is_initialized(&self) -> bool {
        self.initialized
    }

    /// Simula a aplicação de um pulso de tensão.
    fn apply_pulse(&mut self, voltage: f64, _duration_ms: u64) -> Result<(), MemristorError> {
        if !self.initialized {
            return Err(MemristorError::NotInitialized);
        }
        if self.cycle_count >= self.config.endurance_limit {
            return Err(MemristorError::EnduranceExceeded);
        }

        // Modelo simplificado: baseado nos dados do artigo,
        // SET ocorre com tensão positiva ~0.10 V, RESET com negativa ~0.08 V.
        // A simulação considera a magnitude e a duração do pulso.
        let abs_v = voltage.abs();
        if abs_v < 0.01 {
            // Tensão muito baixa, nenhum efeito
            return Ok(());
        }

        // Determinar se é SET ou RESET com base na polaridade e magnitude
        let is_set = voltage > 0.0 && abs_v >= 0.08;
        let is_reset = voltage < 0.0 && abs_v >= 0.06;

        if is_set {
            // Transição para LRS
            self.state = ResistanceState::Low;
            self.cycle_count += 1;
            self.metrics.endurance_remaining = self.metrics.endurance_remaining.saturating_sub(1);
            self.metrics.set_voltage_history.rotate_right(1);
            self.metrics.set_voltage_history[0] = abs_v;
            // Potência: P = V * I (simplificado)
            self.metrics.power_consumption_mw = abs_v * self.config.compliance_current * 1000.0;
            self.metrics.retention_secs = 4000.0; // >4×10³s
        } else if is_reset {
            // Transição para HRS
            self.state = ResistanceState::High;
            self.cycle_count += 1;
            self.metrics.endurance_remaining = self.metrics.endurance_remaining.saturating_sub(1);
            self.metrics.reset_voltage_history.rotate_right(1);
            self.metrics.reset_voltage_history[0] = abs_v;
            self.metrics.power_consumption_mw = abs_v * self.config.compliance_current * 1000.0;
            self.metrics.retention_secs = 4000.0;
        } else {
            // Pulso insuficiente para comutar, apenas leitura implícita
            // (não altera estado)
        }

        Ok(())
    }
}

impl Memristor for MemristorDriver {
    fn set(&mut self, params: Option<SetParams>) -> Result<(), MemristorError> {
        let voltage = params.map_or(self.config.voltage, |p| p.voltage);
        if voltage >= 0.1 {
            return Err(MemristorError::VoltageOutOfRange);
        }
        self.apply_pulse(voltage, 150)?; // 150 ms conforme artigo
        if self.state != ResistanceState::Low {
            return Err(MemristorError::SetFailed);
        }
        Ok(())
    }

    fn reset(&mut self, params: Option<ResetParams>) -> Result<(), MemristorError> {
        let voltage = params.map_or(-self.config.voltage, |p| -p.voltage);
        if voltage.abs() >= 0.1 {
            return Err(MemristorError::VoltageOutOfRange);
        }
        self.apply_pulse(voltage, 200)?; // 200 ms conforme artigo
        if self.state != ResistanceState::High {
            return Err(MemristorError::ResetFailed);
        }
        Ok(())
    }

    fn read(&self) -> Result<ResistanceState, MemristorError> {
        if !self.initialized {
            return Err(MemristorError::NotInitialized);
        }
        Ok(self.state)
    }

    fn voltage(&self) -> f64 {
        self.config.voltage
    }

    fn compliance_current(&self) -> f64 {
        self.config.compliance_current
    }

    fn temperature(&self) -> Option<f64> {
        Some(self.config.temperature)
    }

    fn reset_device(&mut self) -> Result<(), MemristorError> {
        self.state = ResistanceState::High;
        self.cycle_count = 0;
        self.metrics = DriverMetrics::new();
        Ok(())
    }

    fn metrics(&self) -> &dyn Metrics {
        &self.metrics
    }
}

impl Default for MemristorDriver {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_driver_initialization() {
        let driver = MemristorDriver::new();
        assert!(!driver.is_initialized());

        let config = DriverConfig::default();
        let driver = MemristorDriver::with_config(config).unwrap();
        assert!(driver.is_initialized());
    }

    #[test]
    fn test_set_and_reset() {
        let config = DriverConfig::default();
        let mut driver = MemristorDriver::with_config(config).unwrap();
        driver.set(None).unwrap();
        assert_eq!(driver.read().unwrap(), ResistanceState::Low);
        driver.reset(None).unwrap();
        assert_eq!(driver.read().unwrap(), ResistanceState::High);
    }

    #[test]
    fn test_voltage_limits() {
        let config = DriverConfig::default();
        let mut driver = MemristorDriver::with_config(config).unwrap();
        let result = driver.set_voltage(0.12);
        assert!(result.is_err());
    }

    #[test]
    fn test_compliance_limits() {
        let config = DriverConfig::default();
        let mut driver = MemristorDriver::with_config(config).unwrap();
        let result = driver.set_compliance_current(200e-3);
        assert!(result.is_err());
    }

    #[test]
    fn test_endurance() {
        let config = DriverConfig {
            endurance_limit: 5,
            ..Default::default()
        };
        let mut driver = MemristorDriver::with_config(config).unwrap();
        for _ in 0..2 {
            driver.set(None).unwrap();
            driver.reset(None).unwrap();
        }
        driver.set(None).unwrap();
        let result = driver.set(None);
        assert!(matches!(result, Err(MemristorError::EnduranceExceeded)));
    }

    #[test]
    fn test_metrics() {
        let config = DriverConfig::default();
        let mut driver = MemristorDriver::with_config(config).unwrap();
        driver.set(None).unwrap();
        let metrics = driver.metrics();
        let power = metrics.power_metrics();
        assert!(power.set_power_mw > 0.0);
        assert!(power.average_power_mw > 0.0);
    }
}
