#[cfg(feature = "signing")]
use crate::types::SignedArtifact;
use arkhe_core::ArkheError;

/// Verificador de artefatos assinados.
pub struct ArtifactVerifier;

#[cfg(feature = "signing")]
impl ArtifactVerifier {
    pub fn new() -> Self {
        Self
    }

    /// Verifica um artefato assinado.
    pub fn verify<T: serde::Serialize + for<'de> serde::Deserialize<'de>>(
        &self,
        artifact: &SignedArtifact<T>,
    ) -> Result<VerifyResult, ArkheError> {
        use ed25519_dalek::{VerifyingKey, Verifier, Signature};

        let vk = VerifyingKey::from_bytes(&artifact.public_key_bytes)
            .map_err(|e| ArkheError::Internal(format!("Invalid public key: {}", e)))?;

        let serialized = serde_json::to_vec(&artifact.data)
            .map_err(|e| ArkheError::Serialization(e.to_string()))?;

        let signature = Signature::from_bytes(&artifact.signature.signature_bytes);

        match vk.verify(&serialized, &signature) {
            Ok(()) => Ok(VerifyResult {
                valid: true,
                key_id: artifact.signature.key_id.clone(),
                signed_at: artifact.signature.signed_at,
                purpose: artifact.signature.purpose.clone(),
            }),
            Err(_) => Ok(VerifyResult {
                valid: false,
                key_id: artifact.signature.key_id.clone(),
                signed_at: artifact.signature.signed_at,
                purpose: artifact.signature.purpose.clone(),
            }),
        }
    }
}

/// Resultado da verificação.
#[derive(Debug, Clone)]
pub struct VerifyResult {
    pub valid: bool,
    pub key_id: String,
    pub signed_at: chrono::DateTime<chrono::Utc>,
    pub purpose: String,
}
