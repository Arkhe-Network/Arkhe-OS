use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use cathedral_identity::{Did, sign_message};
use sha3::{Digest, Keccak256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    pub index: u64,
    pub timestamp: DateTime<Utc>,
    pub previous_hash: String,
    pub actions: Vec<Action>,
    pub hash: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Action {
    pub id: String,
    pub did: Did,
    pub action_type: String,
    pub data: serde_json::Value,
    pub signature: Vec<u8>,    // Assinatura ML-DSA
    pub proof: Option<String>, // Prova ZK (opcional)
    pub timestamp: DateTime<Utc>,
}

pub struct WormGraphClient {
    private_key: Vec<u8>,
}

impl WormGraphClient {
    pub fn new() -> Self {
        Self {
            private_key: vec![],
        }
    }

    pub async fn get_next_index(&self) -> Result<u64, String> {
        Ok(0) // stub
    }

    pub async fn get_latest_hash(&self) -> Result<String, String> {
        Ok(String::new()) // stub
    }

    pub async fn persist_block(&self, _block: Block) -> Result<(), String> {
        Ok(()) // stub
    }

    pub async fn record_action(
        &self,
        did: &Did,
        action_type: &str,
        data: serde_json::Value,
    ) -> Result<String, String> {
        // 1. Cria ação
        let mut action = Action {
            id: uuid::Uuid::new_v4().to_string(),
            did: did.clone(),
            action_type: action_type.to_string(),
            data,
            signature: vec![], // Será assinada
            proof: None,
            timestamp: chrono::Utc::now(),
        };

        // 2. Assina a ação com ML-DSA
        let signature = sign_message(did, &serde_json::to_vec(&action).map_err(|e| e.to_string())?, &self.private_key)?;
        action.signature = signature;

        let action_id = action.id.clone();

        // 3. Cria bloco
        let mut block = Block {
            index: self.get_next_index().await?,
            timestamp: chrono::Utc::now(),
            previous_hash: self.get_latest_hash().await?,
            actions: vec![action],
            hash: String::new(), // Será calculado
        };

        // 4. Calcula hash do bloco
        let block_bytes = serde_json::to_vec(&block).map_err(|e| e.to_string())?;
        let block_hash = Keccak256::digest(&block_bytes);
        block.hash = hex::encode(block_hash);

        // 5. Persiste bloco
        self.persist_block(block).await?;

        Ok(action_id)
    }
}
