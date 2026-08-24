//! Definição do trait `Memristor` e tipos de erro/estado.

use crate::metrics::Metrics;
use crate::commands::{SetParams, ResetParams};

/// Estados de resistência.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResistanceState {
    /// Estado de baixa resistência (ON, LRS)
    Low,
    /// Estado de alta resistência (OFF, HRS)
    High,
    /// Estado intermediário para multilevel
    Level(usize),
}

/// Erros do memristor.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MemristorError {
    /// Tensão fora da faixa permitida (<0.1V)
    VoltageOutOfRange,
    /// Corrente de compliance fora da faixa (1 µA – 100 mA)
    ComplianceOutOfRange,
    /// Falha na operação SET
    SetFailed,
    /// Falha na operação RESET
    ResetFailed,
    /// Falha na operação READ
    ReadFailed,
    /// Temperatura fora da faixa de operação (293–393 K)
    TemperatureOutOfRange,
    /// Dispositivo não inicializado
    NotInitialized,
    /// Endurance excedida
    EnduranceExceeded,
    /// Parâmetro inválido
    InvalidParameter,
}

impl core::fmt::Display for MemristorError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            Self::VoltageOutOfRange => write!(f, "Voltage must be < 0.1 V"),
            Self::ComplianceOutOfRange => write!(f, "Compliance current must be between 1 µA and 100 mA"),
            Self::SetFailed => write!(f, "SET operation failed"),
            Self::ResetFailed => write!(f, "RESET operation failed"),
            Self::ReadFailed => write!(f, "READ operation failed"),
            Self::TemperatureOutOfRange => write!(f, "Temperature out of range (293–393 K)"),
            Self::NotInitialized => write!(f, "Memristor not initialized"),
            Self::EnduranceExceeded => write!(f, "Endurance limit exceeded"),
            Self::InvalidParameter => write!(f, "Invalid parameter"),
        }
    }
}

#[cfg(feature = "std")]
impl std::error::Error for MemristorError {}

/// Trait principal para o memristor.
pub trait Memristor {
    /// Realiza a operação SET (transição para LRS).
    fn set(&mut self, params: Option<SetParams>) -> Result<(), MemristorError>;

    /// Realiza a operação RESET (transição para HRS).
    fn reset(&mut self, params: Option<ResetParams>) -> Result<(), MemristorError>;

    /// Lê o estado atual de resistência.
    fn read(&self) -> Result<ResistanceState, MemristorError>;

    /// Retorna a tensão atual aplicada.
    fn voltage(&self) -> f64;

    /// Retorna a corrente de compliance configurada.
    fn compliance_current(&self) -> f64;

    /// Retorna a temperatura atual (se disponível).
    fn temperature(&self) -> Option<f64>;

    /// Reseta o dispositivo para o estado inicial (HRS).
    fn reset_device(&mut self) -> Result<(), MemristorError>;

    /// Obtém métricas de desempenho.
    fn metrics(&self) -> &dyn Metrics;
}
