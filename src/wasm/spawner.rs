pub trait WasmSpawner {
    fn spawn(
        &self,
        wasm_bytes: &[u8],
        input: &[u8],
        memory_limit: usize,
        timeout_ms: u64,
    ) -> Result<WasmExecutionResult, WasmError>;
}

#[derive(Debug)]
pub struct WasmExecutionResult {
    pub output: Vec<u8>,
    pub gas_used: u64,
    pub execution_time_ms: u64,
}

#[derive(Debug)]
pub enum WasmError {
    ExecutionError(String),
}
