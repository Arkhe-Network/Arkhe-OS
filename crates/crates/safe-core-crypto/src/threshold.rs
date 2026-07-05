use crate::CryptoError;
use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[async_trait]
pub trait ThresholdSigner: Send + Sync {
    async fn sign(&self, message: &[u8]) -> Result<ThresholdSignature, CryptoError>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdSignature {
    pub bytes: Vec<u8>,
}

/// Implementação Mock para desenvolvimento. NÃO é criptografia real —
/// apenas um hash Blake3 determinístico usado em testes de integração.
pub struct MockSigner;

#[async_trait]
impl ThresholdSigner for MockSigner {
    async fn sign(&self, message: &[u8]) -> Result<ThresholdSignature, CryptoError> {
        Ok(ThresholdSignature {
            bytes: blake3::hash(message).as_bytes().to_vec(),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_signer_is_deterministic() {
        let s = MockSigner;
        let a = s.sign(b"msg").await.unwrap();
        let b = s.sign(b"msg").await.unwrap();
        assert_eq!(a.bytes, b.bytes);
        assert_eq!(a.bytes.len(), 32);
    }
}
