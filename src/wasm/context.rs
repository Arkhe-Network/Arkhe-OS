use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub type ContentHash = [u8; 32];

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WasmCall {
    pub task: String,
    pub timestamp: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AgentContext {
    pub agent_id: [u8; 32],
    pub current_task: String,
    pub history: Vec<WasmCall>,
    pub persisted_data: HashMap<String, Vec<u8>>,
}

impl AgentContext {
    pub fn new(agent_id: [u8; 32]) -> Self {
        Self {
            agent_id,
            current_task: String::new(),
            history: Vec::new(),
            persisted_data: HashMap::new(),
        }
    }
    pub async fn load(_agent_id: &[u8; 32]) -> Result<Self, String> {
        // Load from HashTree using the agent_id as the key
        Ok(Self::new(*_agent_id))
    }

    pub async fn save(&self) -> Result<ContentHash, String> {
        // Serialize and store in HashTree
        Ok([0u8; 32])
    }

    pub fn update_after_execution(&mut self, call: WasmCall, _output: &[u8]) {
        self.history.push(call);
        // Add to history, update persisted_data if needed
    }
}
