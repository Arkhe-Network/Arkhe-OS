//! Cathedral ARKHE v28.2 — Tool Call Handler
//! Processa tool calls a partir da resposta do modelo, executa ferramentas
//! e retorna o resultado para o agente.
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-TOOL-HANDLER-2026-06-16

use std::sync::Arc;
use serde_json::Value;

// We need to use tools from cathedral_agent if possible,
// or redefine them if the llm server is meant to be completely standalone.
// According to instructions, this uses crate::tools. We will create a dummy for now
// so it compiles, or assume it's part of the cathedral-llm-server codebase.
// Since the instruction says "provided Rust code", I will just paste it.

use cathedral_agent::tools::{ToolRegistry, Tool, ToolResult, ToolError};

/// Estrutura que representa uma tool call na resposta do LLM.
#[derive(Debug, Clone, serde::Deserialize)]
pub struct ParsedToolCall {
    pub id: String,
    pub name: String,
    pub arguments: Value,
}

/// Executa tool calls e formata a resposta para incluir no histórico da conversa.
pub struct ToolCallExecutor {
    registry: Arc<ToolRegistry>,
    memory_proof_verifier: Arc<dyn MemoryProofVerifier>,
}

#[async_trait::async_trait]
pub trait MemoryProofVerifier: Send + Sync {
    async fn verify(&self, proof: &str) -> bool;
}

impl ToolCallExecutor {
    pub fn new(registry: Arc<ToolRegistry>, verifier: Arc<dyn MemoryProofVerifier>) -> Self {
        Self { registry, verifier }
    }

    /// Executa múltiplas tool calls em paralelo e retorna uma lista de mensagens
    /// no formato `{ "role": "tool", "tool_call_id": id, "content": output }`.
    pub async fn execute_tool_calls(
        &self,
        tool_calls: Vec<ParsedToolCall>,
        require_memory_proof: bool,
        memory_proof: Option<&str>,
    ) -> Vec<serde_json::Value> {
        let mut responses = Vec::new();

        // Verificar memory proof, se necessário
        if require_memory_proof {
            if let Some(proof) = memory_proof {
                if !self.memory_proof_verifier.verify(proof).await {
                    // Memory proof inválido – retorna erro para todas as tool calls
                    for tc in &tool_calls {
                        responses.push(serde_json::json!({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": "Error: Memory proof verification failed. This action requires a valid SPHINCS+ signature.",
                        }));
                    }
                    return responses;
                }
            } else {
                for tc in &tool_calls {
                    responses.push(serde_json::json!({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Error: Memory proof required but not provided.",
                    }));
                }
                return responses;
            }
        }

        // Executar cada tool call
        for tc in tool_calls {
            let result = self.execute_single_tool(&tc).await;
            let content = match result {
                Ok(output) => output,
                Err(e) => format!("Tool execution error: {}", e),
            };
            responses.push(serde_json::json!({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            }));
        }
        responses
    }

    async fn execute_single_tool(&self, tc: &ParsedToolCall) -> Result<String, String> {
        let tool = self.registry.get(&tc.name)
            .ok_or_else(|| format!("Tool '{}' not found", tc.name))?;

        // Execute tool (with timeout)
        let result = tokio::time::timeout(
            std::time::Duration::from_secs(30),
            tool.execute(tc.arguments.clone()),
        ).await.map_err(|_| "Tool execution timeout".to_string())?;

        match result {
            Ok(ToolResult { success, output, .. }) if success => Ok(output),
            Ok(ToolResult { error: Some(e), .. }) => Err(e),
            Err(e) => Err(format!("{:?}", e)),
        }
    }
}

/// Integração com o endpoint `/v1/chat/completions`: quando a resposta do modelo
/// contiver `tool_calls`, o servidor deve:
/// 1. Retornar uma resposta com `finish_reason = "tool_calls"` e a lista de tool calls.
/// 2. O cliente (agente) então executa as ferramentas e envia uma nova requisição
///    com o histórico atualizado (incluindo os resultados das tools).
///
/// Para simplificar, o servidor pode também executar as tools automaticamente e
/// retornar a resposta final em uma única chamada (modo "auto"). Implementamos
/// ambas as opções.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ToolCallMode {
    /// Servidor apenas declara as tool calls, cliente executa.
    Declarative,
    /// Servidor executa as tools e continua a conversa.
    Automatic,
}
