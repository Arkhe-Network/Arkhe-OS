//! Cathedral ARKHE v28.3 — JSON-RPC Relayer para ConsensusLedger
use async_trait::async_trait;
use reqwest::Client;
use serde_json::json;
use crate::rl::ledger_integration::{ConsensusLedger, LedgerEvent};

pub struct SolanaJsonRpcRelayer {
    endpoint: String,
    program_id: String,
    client: Client,
}

impl SolanaJsonRpcRelayer {
    pub async fn new(endpoint: &str, program_id: &str) -> Result<Self, String> {
        Ok(Self {
            endpoint: endpoint.to_string(),
            program_id: program_id.to_string(),
            client: Client::new(),
        })
    }
}

#[async_trait]
impl ConsensusLedger for SolanaJsonRpcRelayer {
    async fn record_event(&self, event: LedgerEvent) -> Result<(), String> {
        let instruction_data = json!({
            "event_type": event.event_type,
            "payload": event.payload,
            "timestamp": event.timestamp,
            "policy_version": event.policy_version,
            "signature": event.signature.unwrap_or_default(),
        });

        let body = json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                base64::encode(&serde_json::to_vec(&instruction_data).unwrap_or_default())
            ]
        });

        let response = self.client
            .post(&self.endpoint)
            .json(&body)
            .send()
            .await
            .map_err(|e| format!("RPC error: {}", e))?;

        if !response.status().is_success() {
            return Err(format!("RPC returned {}", response.status()));
        }

        let result: serde_json::Value = response.json().await
            .map_err(|e| format!("RPC parse error: {}", e))?;

        if result.get("error").is_some() {
            Err(format!("RPC error: {:?}", result["error"]))
        } else {
            tracing::debug!("Evento registrado on-chain: {:?}", result["result"]);
            Ok(())
        }
    }
}
