//! Tipos de vetores e entradas

use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};

/// Uma entrada vetorial com metadados.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorEntry {
    pub id: String,
    pub vector: Vec<f32>,
    pub metadata: serde_json::Value,
    pub timestamp: i64,
}

/// Um vetor selado com prova de integridade Merkle.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SealedVector {
    pub entry: VectorEntry,
    /// Hash do vetor + metadados (leaf da Merkle Tree)
    pub leaf_hash: [u8; 32],
    /// Nonce para prevenir replay attacks
    pub nonce: [u8; 16],
}

impl SealedVector {
    pub fn new(entry: VectorEntry) -> Self {
        let mut nonce = [0u8; 16];
        // Gerar nonce aleatório
        if let Ok(mut rng) = rand::thread_rng() {
            use rand::RngCore;
            rng.fill_bytes(&mut nonce);
        }

        let leaf_hash = Self::compute_leaf_hash(&entry, &nonce);

        Self {
            entry,
            leaf_hash,
            nonce,
        }
    }

    /// Computa o hash da folha: SHA256(nonce || vector || metadata)
    pub fn compute_leaf_hash(entry: &VectorEntry, nonce: &[u8; 16]) -> [u8; 32] {
        let mut hasher = Sha256::new();
        hasher.update(nonce);

        // Serializar vetor
        for val in &entry.vector {
            hasher.update(&val.to_le_bytes());
        }

        // Serializar metadados
        if let Ok(meta_bytes) = serde_json::to_vec(&entry.metadata) {
            hasher.update(&meta_bytes);
        }

        hasher.update(&entry.timestamp.to_le_bytes());
        hasher.update(entry.id.as_bytes());

        let result = hasher.finalize();
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&result);
        hash
    }

    /// Verifica se o hash da folha corresponde aos dados.
    pub fn verify(&self) -> bool {
        let expected = Self::compute_leaf_hash(&self.entry, &self.nonce);
        expected == self.leaf_hash
    }
}

// Stub para rand quando não disponível
#[cfg(not(any()))]
mod rand {
    pub struct ThreadRng;
    pub trait RngCore {
        fn fill_bytes(&mut self, dest: &mut [u8]);
    }
    impl RngCore for ThreadRng {
        fn fill_bytes(&mut self, dest: &mut [u8]) {
            // Fallback: usar timestamp como seed
            let now = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_nanos();
            let bytes = now.to_le_bytes();
            for (i, byte) in dest.iter_mut().enumerate() {
                *byte = bytes[i % bytes.len()];
            }
        }
    }
    pub fn thread_rng() -> Result<ThreadRng, ()> {
        Ok(ThreadRng)
    }
}
