use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Assinatura de um artefato.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactSignature {
    /// ID da chave que assinou.
    pub key_id: String,
    /// Assinatura bruta (64 bytes em ed25519).
    pub signature_bytes: Vec<u8>,
    /// Timestamp da assinatura.
    pub signed_at: DateTime<Utc>,
    /// Propósito da assinatura (ex: "model-deploy", "policy-change").
    pub purpose: String,
}

/// Artefato assinado — wrapper em torno de T com metadata de assinatura.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedArtifact<T: Serialize + for<'de> Deserialize<'de>> {
    /// Dados do artefato.
    pub data: T,
    /// Assinatura.
    pub signature: ArtifactSignature,
    /// Chave pública do signatário (32 bytes).
    pub public_key_bytes: Vec<u8>,
}
