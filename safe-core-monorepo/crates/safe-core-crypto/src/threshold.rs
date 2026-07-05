// crates/safe-core-crypto/src/threshold.rs
#[async_trait]
pub trait ThresholdSigner: Send + Sync {
    async fn sign(&self, message: &[u8]) -> Result<ThresholdSignature, CryptoError>;
}

pub struct MockThresholdSigner { pub id: u16 }

#[async_trait]
impl ThresholdSigner for MockThresholdSigner {
    async fn sign(&self, message: &[u8]) -> Result<ThresholdSignature, CryptoError> {
        let mut sig = blake3::hash(message).as_bytes().to_vec();
        sig.push(self.id as u8);
        Ok(ThresholdSignature { bytes: sig, signer_ids: vec![self.id] })
    }
}
