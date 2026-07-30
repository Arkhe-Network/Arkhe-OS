use axum::{
    extract::{State, Extension},
    Json,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use cathedral_identity::Did;
use crate::orchestration::Orchestrator;

#[derive(Debug, Deserialize)]
pub struct CompileRequest {
    pub source: String,
    pub version: Option<String>,
    pub optimize: Option<bool>,
    pub runs: Option<u32>,
}

#[derive(Debug, Serialize)]
pub struct CompileResponse {
    pub success: bool,
    pub abi: Option<serde_json::Value>,
    pub bytecode: Option<String>,
    pub bytecode_hash: Option<String>,
    pub proof: Option<String>,
    pub action_id: Option<String>,
    pub error: Option<String>,
}

pub async fn compile_contract(
    State(orchestrator): State<Arc<Orchestrator>>,
    Extension(did): Extension<Did>,
    Json(req): Json<CompileRequest>,
) -> Json<CompileResponse> {
    let result = orchestrator
        .compile_contract(
            &did,
            &req.source,
            req.version.as_deref().unwrap_or("latest"),
            req.optimize.unwrap_or(true),
            req.runs.unwrap_or(200),
        )
        .await;

    match result {
        Ok((abi, bytecode, bytecode_hash, proof, action_id)) => Json(CompileResponse {
            success: true,
            abi: Some(abi),
            bytecode: Some(bytecode),
            bytecode_hash: Some(bytecode_hash),
            proof: Some(proof),
            action_id: Some(action_id),
            error: None,
        }),
        Err(e) => Json(CompileResponse {
            success: false,
            abi: None,
            bytecode: None,
            bytecode_hash: None,
            proof: None,
            action_id: None,
            error: Some(e),
        }),
    }
}
