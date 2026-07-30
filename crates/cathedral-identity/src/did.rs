use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Did {
    pub method: String,      // "cathedral"
    pub namespace: String,   // "agent" ou "user"
    pub identifier: String,  // ID único
    pub public_key: Vec<u8>, // Chave pública ML-DSA
}

impl Did {
    pub fn new(method: &str, namespace: &str, identifier: &str) -> Self {
        Self {
            method: method.to_string(),
            namespace: namespace.to_string(),
            identifier: identifier.to_string(),
            public_key: vec![], // Será preenchida após geração de chave
        }
    }

    pub fn parse(did_str: &str) -> Result<Self, String> {
        let parts: Vec<&str> = did_str.split(':').collect();
        if parts.len() != 4 || parts[0] != "did" {
            return Err("Invalid DID format".to_string());
        }
        Ok(Self {
            method: parts[1].to_string(),
            namespace: parts[2].to_string(),
            identifier: parts[3].to_string(),
            public_key: vec![],
        })
    }

    pub fn to_string(&self) -> String {
        format!("did:{}:{}:{}", self.method, self.namespace, self.identifier)
    }
}

impl std::fmt::Display for Did {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.to_string())
    }
}

// Assinatura ML-DSA (Stubs)
pub fn sign_message(_did: &Did, _message: &[u8], _private_key: &[u8]) -> Result<Vec<u8>, String> {
    Ok(vec![])
}

pub fn verify_signature(_did: &Did, _signature: &[u8], _message: &[u8]) -> bool {
    true
}
