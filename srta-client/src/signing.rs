use ed25519_dalek::{SigningKey, Signer, VerifyingKey, Verifier, Signature};
use rand::rngs::OsRng;

pub type KeyPair = SigningKey;

pub fn generate_keypair() -> KeyPair {
    SigningKey::generate(&mut OsRng)
}

pub struct MySigner {
    keypair: KeyPair,
}

impl MySigner {
    pub fn new(keypair: KeyPair) -> Self {
        Self { keypair }
    }

    pub fn sign(&self, data: &[u8]) -> [u8; 64] {
        self.keypair.sign(data).to_bytes()
    }
}

pub struct MyVerifier {
    public_key: VerifyingKey,
}

impl MyVerifier {
    pub fn from_bytes(bytes: &[u8; 32]) -> Option<Self> {
        VerifyingKey::from_bytes(bytes).ok().map(|pk| Self { public_key: pk })
    }

    pub fn verify(&self, data: &[u8], signature: &[u8; 64]) -> bool {
        let sig = Signature::from_bytes(signature);
        self.public_key.verify(data, &sig).is_ok()
    }
}
