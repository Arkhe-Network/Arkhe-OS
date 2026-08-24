//! Exemplo de integração do memristor com o ecossistema ARKHE.

use crate::{MemristorDriver, MemristorError, Level, Memristor};

/// Exemplo de uso como memória persistente para um agente.
pub struct MemristorStorage {
    mem: MemristorDriver,
    data: [u8; 1024], // Simulação de dados armazenados
}

impl MemristorStorage {
    /// Cria uma nova instância de `MemristorStorage`.
    pub fn new() -> Self {
        let config = crate::driver::DriverConfig::default();
        let mem = MemristorDriver::with_config(config).unwrap();
        Self {
            mem,
            data: [0; 1024],
        }
    }

    /// Escreve um byte em um endereço simbólico.
    pub fn write_byte(&mut self, address: u16, value: u8) -> Result<(), MemristorError> {
        // Simulação: armazena em RAM e programa o memristor com base no valor.
        self.data[address as usize] = value;
        // Programar nível correspondente ao valor (0–7 para 3 bits)
        let level = Level::new(value & 0x07)?;
        self.mem.set_level(level)?;
        Ok(())
    }

    /// Lê um byte de um endereço.
    pub fn read_byte(&self, address: u16) -> Result<u8, MemristorError> {
        // Simulação: lê do memristor o nível e retorna o byte.
        let level = self.mem.read_level()?;
        let value = self.data[address as usize] & 0xF8 | level.0;
        Ok(value)
    }

    /// Retorna métricas do memristor.
    pub fn metrics(&self) -> &dyn crate::metrics::Metrics {
        self.mem.metrics()
    }
}

impl Default for MemristorStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_storage_write_read() {
        let mut storage = MemristorStorage::new();
        storage.write_byte(0, 0xAB).unwrap();
        let val = storage.read_byte(0).unwrap();
        assert_eq!(val & 0x0F, 0x0B); // Mantém os 3 bits baixos do nível
    }
}
