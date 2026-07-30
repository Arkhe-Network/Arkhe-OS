use serde::{Deserialize, Serialize};
use sha3::{Digest, Sha3_256};
use thiserror::Error;

/// Representa uma prova ZK (simulada).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZKProof {
    pub proof_type: String, // "NANOZK-sim" ou "DeepProve-sim"
    pub hash: String,
    pub sampled_len: usize,
    pub original_len: usize,
    pub timestamp: i64,
}

#[derive(Debug, Error)]
pub enum ZKError {
    #[error("Invalid sampling rate")]
    InvalidRate,
    #[error("Proof generation failed")]
    ProofFailed,
    #[error("Text is empty")]
    EmptyText,
}

/// Gateway ZK que simula provas via hash.
pub struct ZKGateway {
    // No protótipo, apenas simula com hash.
    // Futuramente: RISC Zero prover.
}

impl ZKGateway {
    pub fn new() -> Self {
        Self {}
    }

    /// Amostra uma fração do texto (por caracteres).
    pub async fn sample(&self, text: &str, rate: f64) -> Result<String, ZKError> {
        if rate <= 0.0 || rate > 1.0 {
            return Err(ZKError::InvalidRate);
        }
        let chars: Vec<char> = text.chars().collect();
        if chars.is_empty() {
            return Err(ZKError::EmptyText);
        }
        let step = (1.0 / rate).round() as usize;
        let sampled: String = chars.iter().step_by(step).collect();
        Ok(sampled)
    }

    /// Simula prova NANOZK (L1) com hash SHA-3.
    pub async fn prove_nanozk(&self, data: String) -> Result<ZKProof, ZKError> {
        let hash = Sha3_256::digest(data.as_bytes());
        Ok(ZKProof {
            proof_type: "NANOZK-sim".to_string(),
            hash: format!("0x{:x}", hash),
            sampled_len: data.len(),
            original_len: 0, // será preenchido externamente
            timestamp: chrono::Utc::now().timestamp(),
        })
    }

    /// Simula prova DeepProve (L2) com hash SHA-3.
    pub async fn prove_deepprove(&self, data: String) -> Result<ZKProof, ZKError> {
        let hash = Sha3_256::digest(data.as_bytes());
        Ok(ZKProof {
            proof_type: "DeepProve-sim".to_string(),
            hash: format!("0x{:x}", hash),
            sampled_len: data.len(),
            original_len: 0,
            timestamp: chrono::Utc::now().timestamp(),
        })
    }
}
