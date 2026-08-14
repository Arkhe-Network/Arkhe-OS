use crate::error::{AuthError, AuthResult};
use crate::types::{PqKem, PqSignature};
use alloc::vec::Vec;
use rand_core::CryptoRngCore;
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Debug, Clone, PartialEq)]
pub enum SlowPathMessage {
    KemEncapsulate {
        ct: Vec<u8>,
        ephemeral_pk: Vec<u8>,
    },
    KeyRotation {
        new_session_counter: u64,
        signature: Vec<u8>,
        timestamp_ns: u64,
        src_did: [u8; 33],
    },
    BundleAttestation {
        bundle_hash: [u8; 32],
        signature: Vec<u8>,
    },
}

pub struct SlowPathAuth<S: PqSignature, K: PqKem> {
    our_signing_sk: Vec<u8>,
    our_signing_pk: Vec<u8>,
    peer_signing_pk: Option<Vec<u8>>,
    kem: K,
    sig: S,
}

impl<S: PqSignature, K: PqKem> ZeroizeOnDrop for SlowPathAuth<S, K> {}

impl<S: PqSignature, K: PqKem> Drop for SlowPathAuth<S, K> {
    fn drop(&mut self) {
        self.our_signing_sk.zeroize();
    }
}

impl<S: PqSignature, K: PqKem> SlowPathAuth<S, K> {
    pub fn generate(sig: S, kem: K, rng: &mut dyn CryptoRngCore) -> (Self, Vec<u8>) {
        let (_kem_pk, _kem_sk) = kem.keygen(rng);

        let mut our_sk = alloc::vec![0u8; S::PUBLIC_KEY_LEN];
        let mut our_pk = alloc::vec![0u8; S::PUBLIC_KEY_LEN];
        rng.fill_bytes(&mut our_sk);
        rng.fill_bytes(&mut our_pk);

        let auth = Self {
            our_signing_sk: our_sk,
            our_signing_pk: our_pk.clone(),
            peer_signing_pk: None,
            kem,
            sig,
        };
        (auth, our_pk)
    }

    pub fn from_secret_key(sig: S, kem: K, sk: Vec<u8>, pk: Vec<u8>) -> AuthResult<Self> {
        if sk.len() != S::PUBLIC_KEY_LEN || pk.len() != S::PUBLIC_KEY_LEN {
            return Err(AuthError::InvalidKey);
        }
        Ok(Self {
            our_signing_sk: sk,
            our_signing_pk: pk,
            peer_signing_pk: None,
            kem,
            sig,
        })
    }

    pub fn bootstrap_encapsulate(
        &self,
        peer_kem_pk: &[u8],
        rng: &mut dyn CryptoRngCore,
    ) -> (SlowPathMessage, [u8; 32]) {
        let (ct, ss) = self.kem.encapsulate(peer_kem_pk, rng);

        let mut sig_msg = Vec::with_capacity(ct.len() + self.our_signing_pk.len());
        sig_msg.extend_from_slice(&ct);
        sig_msg.extend_from_slice(&self.our_signing_pk);
        let _signature = self.sig.sign(&sig_msg, &self.our_signing_sk);

        (
            SlowPathMessage::KemEncapsulate {
                ct,
                ephemeral_pk: self.our_signing_pk.clone(),
            },
            ss,
        )
    }

    pub fn bootstrap_decapsulate(
        &mut self,
        msg: &SlowPathMessage,
        our_kem_sk: &[u8],
    ) -> AuthResult<([u8; 32], Vec<u8>)> {
        match msg {
            SlowPathMessage::KemEncapsulate { ct, ephemeral_pk } => {
                let ss = self.kem.decapsulate(ct, our_kem_sk)?;

                let mut sig_msg = Vec::with_capacity(ct.len() + ephemeral_pk.len());
                sig_msg.extend_from_slice(ct);
                sig_msg.extend_from_slice(ephemeral_pk);

                self.peer_signing_pk = Some(ephemeral_pk.clone());
                Ok((ss, ephemeral_pk.clone()))
            }
            _ => Err(AuthError::SlowPathVerification),
        }
    }

    pub fn sign_rotation(
        &self,
        new_counter: u64,
        timestamp_ns: u64,
        src_did: &[u8; 33],
    ) -> SlowPathMessage {
        let mut payload = Vec::with_capacity(8 + 8 + 33);
        payload.extend_from_slice(&new_counter.to_le_bytes());
        payload.extend_from_slice(&timestamp_ns.to_le_bytes());
        payload.extend_from_slice(src_did);

        let sig = self.sig.sign(&payload, &self.our_signing_sk);
        SlowPathMessage::KeyRotation {
            new_session_counter: new_counter,
            signature: sig,
            timestamp_ns,
            src_did: *src_did,
        }
    }

    pub fn verify_rotation(&self, msg: &SlowPathMessage, peer_pk: &[u8]) -> AuthResult<u64> {
        match msg {
            SlowPathMessage::KeyRotation {
                new_session_counter,
                signature,
                timestamp_ns,
                src_did,
            } => {
                let mut payload = Vec::with_capacity(8 + 8 + 33);
                payload.extend_from_slice(&new_session_counter.to_le_bytes());
                payload.extend_from_slice(&timestamp_ns.to_le_bytes());
                payload.extend_from_slice(src_did);

                if !self.sig.verify(&payload, signature, peer_pk) {
                    return Err(AuthError::SlowPathVerification);
                }
                Ok(*new_session_counter)
            }
            _ => Err(AuthError::SlowPathVerification),
        }
    }

    pub fn sign_bundle(&self, bundle_hash: &[u8; 32]) -> SlowPathMessage {
        let sig = self.sig.sign(bundle_hash, &self.our_signing_sk);
        SlowPathMessage::BundleAttestation {
            bundle_hash: *bundle_hash,
            signature: sig,
        }
    }

    pub fn verify_bundle(&self, msg: &SlowPathMessage, peer_pk: &[u8]) -> AuthResult<[u8; 32]> {
        match msg {
            SlowPathMessage::BundleAttestation {
                bundle_hash,
                signature,
            } => {
                if !self.sig.verify(bundle_hash, signature, peer_pk) {
                    return Err(AuthError::SlowPathVerification);
                }
                Ok(*bundle_hash)
            }
            _ => Err(AuthError::SlowPathVerification),
        }
    }

    pub fn public_key(&self) -> &[u8] {
        &self.our_signing_pk
    }

    pub fn peer_public_key(&self) -> Option<&[u8]> {
        self.peer_signing_pk.as_deref()
    }
}
