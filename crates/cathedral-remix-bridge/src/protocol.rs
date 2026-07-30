use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileRequest {
    pub source: String,
    pub version: String,
    pub optimize: bool,
    pub runs: u32,
    pub did: String,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileResponse {
    pub success: bool,
    pub abi: Option<serde_json::Value>,
    pub bytecode: Option<String>,
    pub bytecode_hash: Option<String>,
    pub ast: Option<serde_json::Value>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugSessionRequest {
    pub tx_hash: String,
    pub network: String,
    pub did: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugStepRequest {
    pub session_id: String,
    pub step: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugStateResponse {
    pub session_id: String,
    pub current_step: u32,
    pub call_stack: Vec<CallFrame>,
    pub locals: HashMap<String, String>,
    pub storage: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CallFrame {
    pub address: String,
    pub function: String,
    pub pc: u32,
    pub source_location: Option<SourceLocation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SourceLocation {
    pub file: String,
    pub line: u32,
    pub column: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeployRequest {
    pub bytecode: String,
    pub abi: serde_json::Value,
    pub network: String,
    pub from: String,
    pub gas_limit: u64,
    pub did: String,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeployResponse {
    pub success: bool,
    pub contract_address: Option<String>,
    pub transaction_hash: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginCallRequest {
    pub plugin: String,
    pub method: String,
    pub params: serde_json::Value,
    pub did: String,
}
