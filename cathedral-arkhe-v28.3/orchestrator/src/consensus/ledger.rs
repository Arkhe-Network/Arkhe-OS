//! Cathedral ARKHE v28.3 — Consensus Ledger
//! Registra decisões e recompensas on-chain (TemporalChain).
//!
//! Selo: CATHEDRAL-ARKHE-v28.3-LEDGER-2026-06-16

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RewardRecord {
    pub agent_id: String,
    pub task_id: String,
    pub action: String,
    pub reward: f32,
    pub policy_version: u64,
    pub timestamp: u64,
}

pub struct ConsensusLedger {
    // Stub: conexao com banco de dados ou RPC
    records: Vec<RewardRecord>,
}

impl ConsensusLedger {
    pub fn new() -> Self {
        Self {
            records: Vec::new(),
        }
    }

    /// Registra uma recompensa on-chain
    pub async fn record_reward(&mut self, record: RewardRecord) -> Result<(), String> {
        tracing::info!(
            target: "cathedral::ledger",
            agent = %record.agent_id,
            reward = record.reward,
            "Recompensa registrada no ledger on-chain"
        );
        self.records.push(record);
        // Em producao, chamaria RPC para a TemporalChain
        Ok(())
    }
}
