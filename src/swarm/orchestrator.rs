use std::sync::Arc;
use crate::swarm::wasm_agent::WasmSubAgent;
use crate::wasm::context::AgentContext;
use crate::wasm::spawner::WasmSpawner;

pub struct SwarmSpec {
    pub task: String,
}

pub struct SwarmResult {
    pub output: Vec<u8>,
}

pub struct SwarmOrchestrator {
    pub agent_id: [u8; 32],
    pub spawner: Arc<dyn WasmSpawner + Send + Sync>,
}

impl SwarmOrchestrator {
    pub fn new(agent_id: [u8; 32], spawner: Arc<dyn WasmSpawner + Send + Sync>) -> Self {
        Self { agent_id, spawner }
    }

    pub async fn run_wasm_agent(&mut self, wasm_path: &str, spec: SwarmSpec) -> Result<SwarmResult, String> {
        let wasm_bytes = std::fs::read(wasm_path).map_err(|e| e.to_string())?;
        let mut agent = WasmSubAgent::new(wasm_bytes, self.spawner.clone(), AgentContext::new(self.agent_id));
        let output = agent.execute_task(&spec.task).await?;
        Ok(SwarmResult { output })
    }
}
