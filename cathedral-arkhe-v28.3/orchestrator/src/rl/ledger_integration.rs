use async_trait::async_trait;
use serde::{Deserialize, Serialize};

#[async_trait]
pub trait ConsensusLedger: Send + Sync {
    async fn record_event(&self, event: LedgerEvent) -> Result<(), String>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LedgerEvent {
    pub event_type: String,
    pub payload: String,
    pub timestamp: u64,
    pub policy_version: u64,
    pub signature: Option<String>,
}
