// crates/memory-system/src/seal.rs
//! Selagem de memória com Merkle Tree e snapshots assinados

use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};

/// Snapshot do estado da memória.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemorySnapshot {
    pub timestamp: u64,
    pub root_hash: [u8; 32],
    pub tree_size: usize,
    pub signature: Vec<u8>,
    pub verifying_key: Vec<u8>,
}

/// Selador de memória que cria snapshots criptograficamente verificáveis.
pub struct MemorySealer {
    key_id: String,
}

impl MemorySealer {
    pub fn new(key_id: String) -> Self {
        Self { key_id }
    }

    /// Cria um snapshot do estado atual da Merkle Tree.
    pub async fn create_snapshot(
        &self,
        store: &crate::store::MerkleSealedVectorStore,
    ) -> Result<MemorySnapshot, crate::error::MemoryError> {
        let root_hash = store.merkle_root().await
            .ok_or(crate::error::MemoryError::EmptyTree)?;
        let tree_size = store.tree_size().await;

        // Payload para assinatura
        let payload = format!("{}:{}:{}", tree_size, hex::encode(root_hash), chrono::Utc::now().timestamp());
        let digest = Sha256::digest(payload.as_bytes());

        // TODO: Integrar com HSM real para assinatura
        // Por enquanto, placeholder de assinatura
        let signature = digest.to_vec();
        let verifying_key = self.key_id.as_bytes().to_vec();

        Ok(MemorySnapshot {
            timestamp: chrono::Utc::now().timestamp() as u64,
            root_hash,
            tree_size,
            signature,
            verifying_key,
        })
    }

    /// Verifica a integridade de um snapshot.
    pub fn verify_snapshot(&self, snapshot: &MemorySnapshot) -> Result<bool, crate::error::MemoryError> {
        let payload = format!("{}:{}:{}", snapshot.tree_size, hex::encode(snapshot.root_hash), snapshot.timestamp as i64);
        let expected_digest = Sha256::digest(payload.as_bytes());

        // TODO: Verificar assinatura criptográfica real
        // Por enquanto, verifica consistência do payload
        Ok(snapshot.signature == expected_digest.to_vec())
    }
}
