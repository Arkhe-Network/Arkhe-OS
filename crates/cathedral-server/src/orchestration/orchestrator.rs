use std::sync::Arc;
use cathedral_identity::Did;
use cathedral_wormgraph::WormGraphClient;
use cathedral_zk::ZKGateway;
use cathedral_remix_bridge::{RemixClient, CompileRequest, DeployRequest};
use sha3::{Digest, Keccak256};

pub struct Orchestrator {
    remix: Arc<RemixClient>,
    wormgraph: Arc<WormGraphClient>,
    zk: Arc<ZKGateway>,
}

impl Orchestrator {
    pub fn new(
        remix: Arc<RemixClient>,
        wormgraph: Arc<WormGraphClient>,
        zk: Arc<ZKGateway>,
    ) -> Self {
        Self { remix, wormgraph, zk }
    }

    pub async fn compile_contract(
        &self,
        did: &Did,
        source: &str,
        version: &str,
        optimize: bool,
        runs: u32,
    ) -> Result<(serde_json::Value, String, String, String, String), String> {
        let action_id = self.wormgraph.record_action(
            did,
            "compile_started",
            serde_json::json!({
                "version": version,
                "source_length": source.len(),
                "optimize": optimize,
                "runs": runs,
            }),
        ).await?;

        let req = CompileRequest {
            source: source.to_string(),
            version: version.to_string(),
            optimize,
            runs,
            did: did.to_string(),
            signature: "".to_string(),
        };

        let resp = self.remix.compile(req).await?;
        if !resp.success {
            return Err(resp.error.unwrap_or_else(|| "Compilation failed".to_string()));
        }

        let abi = resp.abi.unwrap_or_else(|| serde_json::json!([]));
        let bytecode = resp.bytecode.unwrap_or_default();
        let bytecode_hash = resp.bytecode_hash.unwrap_or_default();

        let proof = self.zk.prove_statement(
            &format!("Compilação Solidity v{} para DID {}", version, did),
        ).await?;

        self.wormgraph.record_action(
            did,
            "compile_completed",
            serde_json::json!({
                "version": version,
                "bytecode_hash": bytecode_hash,
                "abi": abi,
                "proof": proof,
                "action_id": action_id,
            }),
        ).await?;

        Ok((abi, bytecode, bytecode_hash, proof, action_id))
    }

    pub async fn deploy_contract(
        &self,
        did: &Did,
        bytecode: &str,
        abi: &serde_json::Value,
        network: &str,
        from: &str,
        gas_limit: u64,
    ) -> Result<(String, String, String), String> {
        let action_id = self.wormgraph.record_action(
            did,
            "deploy_intent",
            serde_json::json!({
                "network": network,
                "bytecode_hash": hex::encode(Keccak256::digest(bytecode.as_bytes())),
                "from": from,
            }),
        ).await?;

        let req = DeployRequest {
            bytecode: bytecode.to_string(),
            abi: abi.clone(),
            network: network.to_string(),
            from: from.to_string(),
            gas_limit,
            did: did.to_string(),
            signature: "".to_string(),
        };

        let resp = self.remix.deploy(req).await?;
        if !resp.success {
            return Err(resp.error.unwrap_or_else(|| "Deployment failed".to_string()));
        }

        let contract_address = resp.contract_address.unwrap_or_default();
        let tx_hash = resp.transaction_hash.unwrap_or_default();

        self.wormgraph.record_action(
            did,
            "deploy_completed",
            serde_json::json!({
                "network": network,
                "contract_address": contract_address,
                "transaction_hash": tx_hash,
                "action_id": action_id,
            }),
        ).await?;

        Ok((contract_address, tx_hash, action_id))
    }
}
