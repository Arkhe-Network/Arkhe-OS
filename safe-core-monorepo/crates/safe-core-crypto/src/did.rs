// crates/safe-core-crypto/src/did.rs
pub struct DidArkhe {
    uri: String,
    pub_key_hash: [u8; 32],
}

impl DidArkhe {
    pub fn derive(pub_key: &[u8]) -> Result<Self, CryptoError> {
        if pub_key.is_empty() {
            return Err(CryptoError::EmptyPublicKey);
        }
        let hash = blake3::hash(pub_key);
        let uri = format!("did:arkhe:{}", hex::encode(hash.as_bytes()));
        Ok(Self { uri, pub_key_hash: hash.into() })
    }
}
