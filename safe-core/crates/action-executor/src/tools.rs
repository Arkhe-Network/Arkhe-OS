//! Ferramentas executáveis (Shell, HTTP, Python)

use async_trait::async_trait;
use serde_json::Value;
use crate::error::ExecError;
use crate::sandbox::{SandboxExecutor, ExecutionResult};
use crate::gate::ExecutionGate;
use std::path::PathBuf;

/// Resultado da execução de uma ferramenta.
#[derive(Debug, Clone)]
pub struct ToolResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

/// Trait para ferramentas executáveis.
#[async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &'static str;
    async fn execute(&self, params: &Value) -> Result<ToolResult, ExecError>;
}

/// Executa comandos shell em sandbox.
pub struct ShellTool {
    sandbox: SandboxExecutor,
}

impl ShellTool {
    pub fn new(gate: ExecutionGate) -> Self {
        Self {
            sandbox: SandboxExecutor::new(gate),
        }
    }
}

#[async_trait]
impl Tool for ShellTool {
    fn name(&self) -> &'static str { "shell" }

    async fn execute(&self, params: &Value) -> Result<ToolResult, ExecError> {
        let cmd = params.get("cmd")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ExecError::MissingParam("cmd".into()))?;

        let interpreter = params.get("interpreter")
            .and_then(|v| v.as_str())
            .unwrap_or("bash");

        let result = self.sandbox.execute_code(cmd, interpreter)?;

        Ok(ToolResult {
            stdout: result.stdout,
            stderr: result.stderr,
            exit_code: result.exit_code,
        })
    }
}

/// Executa chamadas HTTP.
pub struct HttpTool {
    gate: ExecutionGate,
}

impl HttpTool {
    pub fn new(gate: ExecutionGate) -> Self {
        Self { gate }
    }
}

#[async_trait]
impl Tool for HttpTool {
    fn name(&self) -> &'static str { "http" }

    async fn execute(&self, params: &Value) -> Result<ToolResult, ExecError> {
        let url = params.get("url")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ExecError::MissingParam("url".into()))?;

        let method = params.get("method")
            .and_then(|v| v.as_str())
            .unwrap_or("GET");

        let body = params.get("body").cloned();

        let sandbox = SandboxExecutor::new(self.gate.clone());
        let json = sandbox.execute_api(url, method, body).await?;

        Ok(ToolResult {
            stdout: serde_json::to_string_pretty(&json).unwrap_or_default(),
            stderr: String::new(),
            exit_code: 0,
        })
    }
}

/// Executa scripts Python em sandbox.
pub struct PythonTool {
    sandbox: SandboxExecutor,
}

impl PythonTool {
    pub fn new(gate: ExecutionGate) -> Self {
        Self {
            sandbox: SandboxExecutor::new(gate),
        }
    }
}

#[async_trait]
impl Tool for PythonTool {
    fn name(&self) -> &'static str { "python" }

    async fn execute(&self, params: &Value) -> Result<ToolResult, ExecError> {
        let code = params.get("code")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ExecError::MissingParam("code".into()))?;

        let result = self.sandbox.execute_code(code, "python3")?;

        Ok(ToolResult {
            stdout: result.stdout,
            stderr: result.stderr,
            exit_code: result.exit_code,
        })
    }
}
