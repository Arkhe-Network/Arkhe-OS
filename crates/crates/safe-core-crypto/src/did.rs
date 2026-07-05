use serde::{Deserialize, Serialize};

/// DID:arkhe baseado puramente em hash Blake3.
/// Formato: `did:arkhe:<hex_blake3(pub_key)>`
///
/// Não depende de UUID. Determinístico. Imutável.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct DidArkhe {
    uri: String,
    pub_key_hash: [u8; 32],
}

impl DidArkhe {
    pub fn derive(pub_key: &[u8]) -> Result<Self, crate::CryptoError> {
        if pub_key.is_empty() {
            return Err(crate::CryptoError::EmptyPublicKey);
        }
        let hash = blake3::hash(pub_key);
        let uri = format!("did:arkhe:{}", hex::encode(hash.as_bytes()));
        Ok(Self {
            uri,
            pub_key_hash: hash.into(),
        })
    }

    pub fn uri(&self) -> &str {
        &self.uri
    }

    pub fn pub_key_hash(&self) -> &[u8; 32] {
        &self.pub_key_hash
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_did_determinism() {
        let key = b"test_key";
        let did1 = DidArkhe::derive(key).unwrap();
        let did2 = DidArkhe::derive(key).unwrap();
        assert_eq!(did1, did2);
    }

    #[test]
    fn test_did_empty_key_fails() {
        assert!(DidArkhe::derive(b"").is_err());
    }

    #[test]
    fn test_did_uri_shape() {
        let did = DidArkhe::derive(b"test_key").unwrap();
        assert!(did.uri().starts_with("did:arkhe:"));
        // "did:arkhe:" tem 10 caracteres; o hash hex tem 64.
        assert_eq!(did.uri()[10..].len(), 64);
    }
}
