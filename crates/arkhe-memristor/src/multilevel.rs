//! Suporte a armazenamento multilevel (MLC) via ajuste da corrente de compliance.

use crate::{MemristorError, MemristorDriver, Memristor};
use num_traits::real::Real;

/// Nível de resistência programável (0–7, 3 bits).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Level(pub u8);

impl Level {
    /// Cria um nível a partir de um valor de 0 a 7.
    pub fn new(value: u8) -> Result<Self, MemristorError> {
        if value > 7 {
            return Err(MemristorError::InvalidParameter);
        }
        Ok(Self(value))
    }

    /// Retorna a corrente de compliance correspondente a este nível.
    /// Níveis 0–7 mapeiam para correntes de 10 µA a 100 mA (escala log).
    pub fn compliance_current(&self) -> f64 {
        // Mapeamento logarítmico: nível 0 → 10 µA, nível 7 → 100 mA
        let min_current = 10e-6;   // 10 µA
        let max_current = 100e-3;  // 100 mA
        let ratio = (self.0 as f64) / 7.0;
        min_current * (max_current / min_current).powf(ratio)
    }
}

impl MemristorDriver {
    /// Programa um nível de resistência específico (0–7).
    pub fn set_level(&mut self, level: Level) -> Result<(), MemristorError> {
        let cc = level.compliance_current();
        self.set_compliance_current(cc)?;
        self.set(None)?;
        // O estado atual é LRS, mas o nível é registrado internamente
        // Aqui poderíamos armazenar o nível em um campo, mas para simplicidade,
        // usamos o estado Low com metadados.
        Ok(())
    }

    /// Lê o nível programado (simulado).
    pub fn read_level(&self) -> Result<Level, MemristorError> {
        // Na prática, mediríamos a corrente de leitura.
        // Simulação: retorna um nível baseado na corrente de compliance atual.
        let cc = self.compliance_current();
        // Mapeamento inverso (aproximado)
        let min_current = 10e-6;
        let max_current = 100e-3;
        let ratio = (cc / min_current).log10() / (max_current / min_current).log10();
        let level = (ratio * 7.0).round() as u8;
        Level::new(level.min(7))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_level_compliance() {
        let level0 = Level::new(0).unwrap();
        assert!((level0.compliance_current() - 10e-6).abs() < 1e-9);

        let level7 = Level::new(7).unwrap();
        assert!((level7.compliance_current() - 100e-3).abs() < 1e-6);

        let level3 = Level::new(3).unwrap();
        let cc = level3.compliance_current();
        assert!(cc > 10e-6 && cc < 100e-3);
    }

    #[test]
    fn test_set_level() {
        let config = crate::driver::DriverConfig::default();
        let mut driver = MemristorDriver::with_config(config).unwrap();

        driver.set_level(Level::new(3).unwrap()).unwrap();
        assert_eq!(driver.read_level().unwrap().0, 3);
    }
}
