use crate::error::AuthResult;
use alloc::vec::Vec;
use rand_core::CryptoRngCore;
use zeroize::Zeroize;

pub trait PqSignature {
    const PUBLIC_KEY_LEN: usize;
    const SIGNATURE_LEN: usize;
    fn sign(&self, msg: &[u8], sk: &[u8]) -> Vec<u8>;
    fn verify(&self, msg: &[u8], sig: &[u8], pk: &[u8]) -> bool;
}

pub trait PqKem {
    const CT_LEN: usize;
    const SS_LEN: usize = 32;
    fn keygen(&self, rng: &mut dyn CryptoRngCore) -> (Vec<u8>, Vec<u8>);
    fn encapsulate(&self, pk: &[u8], rng: &mut dyn CryptoRngCore) -> (Vec<u8>, [u8; 32]);
    fn decapsulate(&self, ct: &[u8], sk: &[u8]) -> AuthResult<[u8; 32]>;
}

pub trait FastAead {
    const KEY_LEN: usize = 32;
    const NONCE_LEN: usize = 12;
    const TAG_LEN: usize = 16;
    fn seal(&self, key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], plaintext: &mut [u8]) -> [u8; 16];
    fn open(
        &self,
        key: &[u8; 32],
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext: &mut [u8],
        tag: &[u8; 16],
    ) -> AuthResult<()>;
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct NodeId(pub [u8; 33]);

impl NodeId {
    pub fn new(prefix: u8, hash: &[u8; 32]) -> Self {
        let mut bytes = [0u8; 33];
        bytes[0] = prefix;
        bytes[1..].copy_from_slice(hash);
        Self(bytes)
    }
    pub fn hash(&self) -> &[u8; 32] {
        self.0[1..].try_into().expect("33-1=32")
    }
    pub fn prefix(&self) -> u8 {
        self.0[0]
    }
}

impl core::fmt::Debug for NodeId {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "NodeId({:02x?}...)", &self.0[..4])
    }
}

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Zeroize)]
pub struct StorageHandle(pub u64);

impl core::fmt::Debug for StorageHandle {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "StorageHandle({})", self.0)
    }
}
