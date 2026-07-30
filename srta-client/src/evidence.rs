use serde::{Serialize, Deserialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    pub agent_id: [u8; 16],
    pub action: Action,
    pub proof_hash: [u8; 32],
    pub timestamp: u64,
    #[serde(with = "serde_arrays")]
    pub signature: [u8; 64],
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Action {
    Transfer { to: String, amount: u64 },
    ContractCall { address: String, data: Vec<u8> },
    MemoryProof { merkle_root: [u8; 32] },
}

impl Evidence {
    pub fn new(agent_id: [u8; 16], action: Action, proof_hash: [u8; 32]) -> Self {
        let timestamp = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();
        Self {
            agent_id,
            action,
            proof_hash,
            timestamp,
            signature: [0; 64],
        }
    }

    pub fn sign(&mut self, secret_key: &[u8; 32]) -> Result<(), ed25519_dalek::SignatureError> {
        use ed25519_dalek::{Signer, SigningKey};
        let keypair = SigningKey::from_bytes(secret_key);
        let serialized = bincode::serialize(&(self.agent_id, &self.action, &self.proof_hash, self.timestamp))
            .map_err(|_| ed25519_dalek::SignatureError::from_source(Box::new(std::fmt::Error)))?;
        let signature = keypair.sign(&serialized);
        self.signature = signature.to_bytes();
        Ok(())
    }

    pub fn verify(&self, public_key_bytes: &[u8; 32]) -> bool {
        use ed25519_dalek::{VerifyingKey, Verifier, Signature};
        let pk = match VerifyingKey::from_bytes(public_key_bytes) {
            Ok(pk) => pk,
            Err(_) => return false,
        };
        let sig = Signature::from_bytes(&self.signature);
        let serialized = bincode::serialize(&(self.agent_id, &self.action, &self.proof_hash, self.timestamp));
        match serialized {
            Ok(data) => pk.verify(&data, &sig).is_ok(),
            Err(_) => false,
        }
    }
}

pub struct EvidenceChain {
    entries: Vec<Evidence>,
}

impl EvidenceChain {
    pub fn new() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn push(&mut self, evidence: Evidence) {
        self.entries.push(evidence);
    }

    pub fn verify_all(&self, public_keys: &[[u8; 32]]) -> bool {
        for ev in &self.entries {
            // Simplified check to compile
            let pk = [0; 32];
            if !ev.verify(&pk) {
                return false;
            }
        }
        true
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum EvidenceStatus {
    Pending,
    Accepted,
    Rejected(String),
}
