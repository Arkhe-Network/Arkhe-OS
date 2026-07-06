//! Certificado de atestacao do GDID e verificacao criptografica.

use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use serde_big_array::BigArray;
use subtle::ConstantTimeEq;

use super::Gdid;

/// Bitmap de capacidades do dispositivo (16 bits).
#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct CapabilityBitmap(pub u16);

impl CapabilityBitmap {
    /// Permite participar do consenso.
    pub const CONSENSUS: u16 = 0x0001;
    /// Permite executar inferencia.
    pub const INFERENCE: u16 = 0x0002;
    /// Permite votar em governanca.
    pub const GOVERNANCE_VOTE: u16 = 0x0004;
    /// Permite atuar como relay Hubble.
    pub const HUBBLE_RELAY: u16 = 0x0008;

    /// Verifica se todas as flags de `mask` estao presentes.
    pub fn has(&self, mask: u16) -> bool {
        self.0 & mask == mask
    }
}

/// Erros especificos do GDID.
#[derive(Debug, thiserror::Error)]
pub enum GdidError {
    /// O certificado expirou.
    #[error("GDID certificate expired at {expired_at}")]
    Expired {
        /// Timestamp Unix de expiracao.
        expired_at: u64,
    },
    /// A assinatura do issuer nao e valida para o payload.
    #[error("Invalid issuer signature")]
    InvalidSignature,
    /// O GDID reconstruido nao corresponde ao GDID do certificado.
    #[error("GDID hash mismatch: derived does not match certificate")]
    GdidMismatch,
    /// Namespace fora do intervalo suportado.
    #[error("Invalid namespace: {0}")]
    InvalidNamespace(u8),
    /// Versao fora do intervalo suportado.
    #[error("Invalid version: {0}")]
    InvalidVersion(u8),
    /// A prova de revogacao (Merkle) nao pode ser verificada contra a raiz.
    #[error("Invalid revocation proof")]
    InvalidProof,
}

/// Certificado de atestacao do GDID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GdidCertificate {
    /// O GDID atestado.
    pub gdid: Gdid,
    /// Chave publica Ed25519 do dispositivo.
    pub pubkey: [u8; 32],
    /// Timestamp de emissao (Unix).
    pub issued_at: u64,
    /// Timestamp de expiracao (Unix).
    pub expires_at: u64,
    /// Namespace do dispositivo.
    pub namespace: u8,
    /// Capacidades permitidas.
    pub capabilities: CapabilityBitmap,
    /// Assinatura do issuer (64 bytes).
    #[serde(with = "BigArray")]
    pub issuer_sig: [u8; 64],
}

/// Payload serializado para verificacao de assinatura (exclui `issuer_sig`).
#[derive(Serialize)]
struct GdidCertPayload {
    gdid_bytes: [u8; 32],
    pubkey: [u8; 32],
    issued_at: u64,
    expires_at: u64,
    namespace: u8,
    capabilities: u16,
}

impl GdidCertificate {
    fn payload(&self) -> GdidCertPayload {
        GdidCertPayload {
            gdid_bytes: *self.gdid.as_bytes(),
            pubkey: self.pubkey,
            issued_at: self.issued_at,
            expires_at: self.expires_at,
            namespace: self.namespace,
            capabilities: self.capabilities.0,
        }
    }

    /// Verifica a assinatura do issuer e a integridade do certificado.
    ///
    /// `now` e o timestamp Unix corrente, fornecido pelo chamador para manter
    /// a funcao pura e testavel (sem depender de `SystemTime::now()` aqui).
    pub fn verify(&self, issuer_pubkey: &VerifyingKey, now: u64) -> Result<(), GdidError> {
        if now > self.expires_at {
            return Err(GdidError::Expired { expired_at: self.expires_at });
        }

        if self.namespace > Gdid::NS_OEM {
            return Err(GdidError::InvalidNamespace(self.namespace));
        }

        if self.gdid.version() > Gdid::VERSION_ML_DSA_65 {
            return Err(GdidError::InvalidVersion(self.gdid.version()));
        }

        let payload = postcard::to_allocvec(&self.payload()).map_err(|_| GdidError::InvalidSignature)?;

        let sig = Signature::from_slice(&self.issuer_sig).map_err(|_| GdidError::InvalidSignature)?;

        issuer_pubkey.verify(&payload, &sig).map_err(|_| GdidError::InvalidSignature)?;

        // Cross-check: o GDID no certificado deve corresponder aos campos
        // canonicos reconstruidos (versao/namespace/hash/nonce), comparados
        // em tempo constante para nao vazar informacao por timing.
        let expected_gdid =
            Gdid::from_parts(self.gdid.version(), self.namespace, &self.gdid.hw_hash(), self.gdid.nonce());

        if expected_gdid.as_bytes().ct_eq(self.gdid.as_bytes()).unwrap_u8() == 0 {
            return Err(GdidError::GdidMismatch);
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::{Signer, SigningKey};

    fn issue(gdid: Gdid, signing_key: &SigningKey, expires_at: u64) -> GdidCertificate {
        let mut cert = GdidCertificate {
            gdid,
            pubkey: signing_key.verifying_key().to_bytes(),
            issued_at: 0,
            expires_at,
            namespace: gdid.namespace(),
            capabilities: CapabilityBitmap(CapabilityBitmap::INFERENCE),
            issuer_sig: [0u8; 64],
        };
        let payload = postcard::to_allocvec(&cert.payload()).unwrap();
        let sig = signing_key.sign(&payload);
        cert.issuer_sig = sig.to_bytes();
        cert
    }

    #[test]
    fn valid_certificate_verifies() {
        let signing_key = SigningKey::from_bytes(&[3u8; 32]);
        let hw = [5u8; 20];
        let gdid = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &hw, 1);
        let cert = issue(gdid, &signing_key, 1_000_000);

        assert!(cert.verify(&signing_key.verifying_key(), 500_000).is_ok());
    }

    #[test]
    fn expired_certificate_is_rejected() {
        let signing_key = SigningKey::from_bytes(&[3u8; 32]);
        let hw = [5u8; 20];
        let gdid = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &hw, 1);
        let cert = issue(gdid, &signing_key, 100);

        let err = cert.verify(&signing_key.verifying_key(), 200).unwrap_err();
        assert!(matches!(err, GdidError::Expired { expired_at: 100 }));
    }

    #[test]
    fn tampered_payload_fails_signature_check() {
        let signing_key = SigningKey::from_bytes(&[3u8; 32]);
        let hw = [5u8; 20];
        let gdid = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &hw, 1);
        let mut cert = issue(gdid, &signing_key, 1_000_000);
        cert.capabilities = CapabilityBitmap(CapabilityBitmap::GOVERNANCE_VOTE);

        let err = cert.verify(&signing_key.verifying_key(), 500_000).unwrap_err();
        assert!(matches!(err, GdidError::InvalidSignature));
    }

    #[test]
    fn wrong_issuer_key_is_rejected() {
        let signing_key = SigningKey::from_bytes(&[3u8; 32]);
        let other_key = SigningKey::from_bytes(&[9u8; 32]);
        let hw = [5u8; 20];
        let gdid = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_ARKHE, &hw, 1);
        let cert = issue(gdid, &signing_key, 1_000_000);

        let err = cert.verify(&other_key.verifying_key(), 500_000).unwrap_err();
        assert!(matches!(err, GdidError::InvalidSignature));
    }
}
