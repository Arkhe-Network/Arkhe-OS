use crate::mhd::EvoField;
use crate::retro::EchoSignal;
use crate::shadow::Shadow;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Identificador criptográfico do estado da Sombra
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ShadowHash(pub [u8; 32]);

impl ShadowHash {
    /// Gera o hash da Sombra a partir dos valores singulares da cauda
    pub fn from_singular_values(tail_singular: &[f64]) -> Self {
        let mut hasher = Sha256::new();
        for &val in tail_singular {
            hasher.update(val.to_le_bytes());
        }
        let result = hasher.finalize();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&result);
        Self(hash)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeBlock {
    pub height: u64,
    pub timestamp_phase: f64,
    pub helicity: f64,
    pub delta_helicity: f64,
    pub shadow: Shadow,
    pub shadow_hash: ShadowHash,
    pub echo_signature: EchoSignal,
    pub transactions: Vec<String>, // Simples placeholder
}

impl TimeBlock {
    pub fn new(height: u64, field: &EvoField, shadow: Shadow, echo: EchoSignal) -> Self {
        let h = field.helicity();
        Self {
            height,
            timestamp_phase: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
            helicity: h,
            delta_helicity: 0.0, // Preenchido pelo validador
            shadow_hash: ShadowHash::from_singular_values(
                shadow.tail_singular.as_slice().unwrap_or(&[]),
            ),
            shadow,
            echo_signature: echo,
            transactions: Vec::new(),
        }
    }
}

/// Oráculo de Alfvén — validação por Loop de Chern-Simons
pub struct ChernSimonsOracle {
    pub tolerance: f64,
}

impl ChernSimonsOracle {
    pub fn new(tolerance: f64) -> Self {
        Self { tolerance }
    }

    /// Verifica se um bloco forma um loop fechado de Chern-Simons
    pub fn verify(&self, block: &TimeBlock, field: &EvoField) -> bool {
        // Emite o eco do bloco e calcula a helicidade prevista
        let predicted_h = block.echo_signature.predicted_helicity;
        let actual_h = field.helicity();
        let delta = (predicted_h - actual_h).abs();
        delta < self.tolerance
    }
}
