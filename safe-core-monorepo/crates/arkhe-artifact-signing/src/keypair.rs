//! ✅ F1: Usa API v2.2.0 do ed25519-dalek.
//!
//! API v1.x (DEPRECATED):
//!   let keypair = Keypair::generate(&mut OsRng);
//!   keypair.public
//!   keypair.sign(message)
//!   keypair.verify(message, &sig)
//!
//! API v2.2.0 (CORRETA):
//!   let signing_key = SigningKey::generate(&mut OsRng);
//!   let verifying_key = signing_key.verifying_key();
//!   let signature = signing_key.sign(message);
//!   verifying_key.verify(message, &signature)

use crate::types::{ArtifactSignature, SignedArtifact};
use arkhe_core::ArkheError;
use chrono::Utc;

#[cfg(feature = "signing")]
use ed25519_dalek::{SigningKey, VerifyingKey, Signer, Verifier, Signature};
#[cfg(feature = "signing")]
use rand::rngs::OsRng;

/// Par de chaves para assinatura de artefatos.
#[cfg(feature = "signing")]
pub struct ArtifactKeyPair {
    /// Chave de assinatura (PRIVADA — nunca expor esta).
    signing_key: SigningKey,
    /// Chave de verificação (PÚBLICA).
    verifying_key: VerifyingKey,
    /// ID da chave.
    key_id: String,
}

#[cfg(feature = "signing")]
impl ArtifactKeyPair {
    /// Gera novo par de chaves.
    ///
    /// ✅ F1: Usa SigningKey::generate() (v2.2.0), NÃO Keypair::generate() (v1.x).
    pub fn generate() -> Result<Self, ArkheError> {
        let mut rng = OsRng;
        let signing_key = SigningKey::generate(&mut rng);
        let verifying_key = signing_key.verifying_key();
        let key_id = uuid::Uuid::new_v4().to_string();

        Ok(Self {
            signing_key,
            verifying_key,
            key_id,
        })
    }

    /// Retorna a chave pública como bytes (32 bytes).
    pub fn public_key_bytes(&self) -> Vec<u8> {
        self.verifying_key.to_bytes().to_vec()
    }

    /// Retorna o ID da chave.
    pub fn key_id(&self) -> &str {
        &self.key_id
    }

    /// Assina dados serializados.
    pub fn sign(&self, data: &[u8], purpose: &str) -> Result<ArtifactSignature, ArkheError> {
        let signature: Signature = self.signing_key.sign(data);
        Ok(ArtifactSignature {
            key_id: self.key_id.clone(),
            signature_bytes: signature.to_bytes().to_vec(),
            signed_at: Utc::now(),
            purpose: purpose.to_string(),
        })
    }

    /// Cria um artefato assinado.
    pub fn sign_artifact<T: serde::Serialize>(
        &self,
        data: &T,
        purpose: &str,
    ) -> Result<SignedArtifact<T>, ArkheError> {
        let serialized = serde_json::to_vec(data)
            .map_err(|e| ArkheError::Serialization(e.to_string()))?;
        let signature = self.sign(&serialized, purpose)?;
        Ok(SignedArtifact {
            data: data.clone(),
            signature,
            public_key_bytes: self.public_key_bytes(),
        })
    }
}

#[cfg(feature = "signing")]
impl Drop for ArtifactKeyPair {
    fn drop(&mut self) {
        // ✅ Zeroize a chave privada após uso (segurança)
        use zeroize::Zeroize;
        self.signing_key.as_mut_bytes().zeroize();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(feature = "signing")]
    #[test]
    fn test_generate_and_sign() {
        let kp = ArtifactKeyPair::generate().unwrap();
        assert!(!kp.key_id.is_empty());
        assert_eq!(kp.public_key_bytes().len(), 32);
    }

    #[cfg(feature = "signing")]
    #[test]
    fn test_sign_and_verify() {
        let kp = ArtifactKeyPair::generate().unwrap();
        let data = b"hello world";

        let sig = kp.sign(data, "test").unwrap();
        assert_eq!(sig.signature_bytes.len(), 64);

        // Verificar
        let vk = kp.verifying_key.clone();
        let signature = Signature::from_bytes(&sig.signature_bytes);
        assert!(vk.verify(data, &signature).is_ok());
    }

    #[cfg(feature = "signing")]
    #[test]
    fn test_sign_artifact_roundtrip() {
        let kp = ArtifactKeyPair::generate().unwrap();
        let artifact = serde_json::json!({"name": "test-model", "version": "1.0"});

        let signed = kp.sign_artifact(&artifact, "model-deploy").unwrap();
        assert_eq!(signed.signature.key_id, kp.key_id());
        assert_eq!(signed.public_key_bytes.len(), 32);

        // Verificar
        let serialized = serde_json::to_vec(&signed.data).unwrap();
        let signature = Signature::from_bytes(&signed.signature.signature_bytes);
        let vk = kp.verifying_key.clone();
        assert!(vk.verify(&serialized, &signature).is_ok());
    }

    #[cfg(feature = "signing")]
    #[test]
    fn test_tampered_data_fails_verify() {
        let kp = ArtifactKeyPair::generate().unwrap();
        let data = b"original message";
        let sig = kp.sign(data, "test").unwrap();

        let signature = Signature::from_bytes(&sig.signature_bytes);
        let vk = kp.verifying_key.clone();
        // Dados diferentes → verificação falha
        assert!(vk.verify(b"tampered message", &signature).is_err());
    }
}
