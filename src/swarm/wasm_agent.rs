use std::sync::Arc;
use crate::wasm::spawner::{WasmSpawner, WasmExecutionResult, WasmError};
use crate::wasm::context::{AgentContext, WasmCall};

pub struct WasmSubAgent {
    wasm_bytes: Vec<u8>,
    spawner: Arc<dyn WasmSpawner + Send + Sync>,
    context: AgentContext,
}

impl WasmSubAgent {
    pub fn new(wasm_bytes: Vec<u8>, spawner: Arc<dyn WasmSpawner + Send + Sync>, context: AgentContext) -> Self {
        Self {
            wasm_bytes,
            spawner,
            context,
        }
    }
    pub async fn execute_task(&mut self, task: &str) -> Result<Vec<u8>, String> {
        let input = task.as_bytes();
        let result = self.spawner.spawn(&self.wasm_bytes, input, 1024 * 1024 * 10, 1000)
            .map_err(|e| format!("{:?}", e))?;

        self.context.update_after_execution(WasmCall {
            task: task.to_string(),
            timestamp: 0,
        }, &result.output);

        let _ = self.context.save().await;

        Ok(result.output)
    }
}
