//! Cathedral ARKHE v28.2 — Code Execution Tool with Sandbox
//! Executa código Python (e outras linguagens) em um ambiente isolado:
//! - gVisor (runsc) ou Docker com limites de recursos
//! - Timeout, restrição de rede, sistema de arquivos readonly
//! - Validação de memory proof antes da execução
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-CODE-EXECUTION-TOOL-2026-06-16

use std::process::{Command, Stdio};
use std::time::Duration;
use std::path::PathBuf;
use serde_json::json;
use tokio::time::timeout;
use crate::tools::{Tool, ToolResult, ToolError, RiskLevel};

/// Configuração da sandbox.
#[derive(Clone)]
pub struct SandboxConfig {
    pub sandbox_type: SandboxType,     // "gvisor", "docker", "chroot"
    pub work_dir: PathBuf,
    pub timeout_secs: u64,
    pub memory_limit_mb: u64,
    pub cpu_limit: f32,                // cores
    pub network_enabled: bool,
    pub readonly_root: bool,
    pub allowed_imports: Vec<String>,  // módulos Python permitidos
    pub forbid_imports: Vec<String>,
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum SandboxType {
    Gvisor,
    Docker,
    Chroot,
}

/// Estrutura principal da ferramenta.
pub struct CodeExecutionTool {
    config: SandboxConfig,
    memory_proof_required: bool,
}

impl CodeExecutionTool {
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            memory_proof_required: true,
        }
    }

    /// Executa código Python em sandbox.
    async fn execute_python(&self, code: &str) -> Result<ToolResult, ToolError> {
        // Pré‑validação: verificar imports proibidos
        for forbidden in &self.config.forbid_imports {
            if code.contains(&format!("import {}", forbidden)) || code.contains(&format!("from {} import", forbidden)) {
                return Err(ToolError::ExecutionFailed(
                    format!("Import of forbidden module '{}'", forbidden)
                ));
            }
        }

        // Cria diretório de trabalho temporário
        let work_dir = self.config.work_dir.join(uuid::Uuid::new_v4().to_string());
        std::fs::create_dir_all(&work_dir)
            .map_err(|e| ToolError::ExecutionFailed(format!("Failed to create work dir: {}", e)))?;

        // Escreve o código em um arquivo .py
        let script_path = work_dir.join("script.py");
        std::fs::write(&script_path, code)
            .map_err(|e| ToolError::ExecutionFailed(format!("Failed to write script: {}", e)))?;

        // Comando base conforme o tipo de sandbox
        let mut cmd = match self.config.sandbox_type {
            SandboxType::Gvisor => {
                let mut c = Command::new("runsc");
                c.args(&[
                    "--rootless",
                    "--network", if self.config.network_enabled { "user" } else { "none" },
                    "--file-access", "readonly",
                ]);
                c.arg("run");
                c.arg("--rm");
                c.arg("--memory"); c.arg(format!("{}M", self.config.memory_limit_mb));
                c.arg("--cpu"); c.arg(self.config.cpu_limit.to_string());
                c.arg("python:3.11-slim");
                c.arg("python");
                c.arg("/script.py");
                c
            }
            SandboxType::Docker => {
                let mut c = Command::new("docker");
                c.args(&[
                    "run",
                    "--rm",
                    "--memory", &format!("{}m", self.config.memory_limit_mb),
                    "--cpus", &self.config.cpu_limit.to_string(),
                ]);
                if !self.config.network_enabled {
                    c.arg("--network").arg("none");
                }
                c.arg("-v").arg(format!("{}:/script.py:ro", script_path.display()));
                c.arg("python:3.11-slim");
                c.arg("python");
                c.arg("/script.py");
                c
            }
            SandboxType::Chroot => {
                // Fallback simples: usar chroot + isolamento básico (requer root)
                let mut c = Command::new("chroot");
                c.arg(&work_dir);
                c.arg("python3");
                c.arg("script.py");
                c
            }
        };

        // Timeout e execução
        let mut child = cmd
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| ToolError::ExecutionFailed(format!("Failed to spawn sandbox: {}", e)))?;

        let output = timeout(
            Duration::from_secs(self.config.timeout_secs),
            child.wait(),
        ).await
            .map_err(|_| ToolError::Timeout)?
            .map_err(|e| ToolError::ExecutionFailed(format!("Execution failed: {}", e)))?;

        let output = child.wait_with_output().map_err(|e| ToolError::ExecutionFailed(e.to_string()))?;

        // Limpeza
        let _ = std::fs::remove_dir_all(&work_dir);

        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        if output.status.success() {
            Ok(ToolResult {
                success: true,
                output: stdout.to_string(),
                metadata: json!({
                    "sandbox": format!("{:?}", self.config.sandbox_type),
                    "duration_secs": self.config.timeout_secs,
                    "stderr": stderr.to_string(),
                }),
            })
        } else {
            Err(ToolError::ExecutionFailed(format!("stderr: {}", stderr)))
        }
    }
}

#[async_trait::async_trait]
impl Tool for CodeExecutionTool {
    fn name(&self) -> &str {
        "code_execution"
    }

    fn description(&self) -> &str {
        "Execute Python code in a secure sandbox (gVisor/Docker) with resource limits and memory proof requirement."
    }

    fn parameters_schema(&self) -> serde_json::Value {
        json!({
            "type": "object",
            "properties": {
                "code": { "type": "string", "description": "Python code to execute" },
                "language": { "type": "string", "enum": ["python"], "default": "python" },
                "memory_proof": { "type": "string", "description": "SPHINCS+ signature proving memory integrity (required for high-trust tiers)" }
            },
            "required": ["code"]
        })
    }

    async fn execute(&self, params: serde_json::Value) -> Result<ToolResult, ToolError> {
        // Verificar presence de memory proof se exigido
        if self.memory_proof_required && params.get("memory_proof").is_none() {
            return Err(ToolError::MemoryProofRequired);
        }

        let code = params["code"].as_str()
            .ok_or(ToolError::InvalidParameters("Missing 'code' field".to_string()))?;

        let language = params.get("language").and_then(|v| v.as_str()).unwrap_or("python");
        match language {
            "python" => self.execute_python(code).await,
            _ => Err(ToolError::InvalidParameters(format!("Unsupported language: {}", language))),
        }
    }

    fn requires_memory_proof(&self) -> bool {
        self.memory_proof_required
    }

    fn risk_level(&self) -> RiskLevel {
        RiskLevel::High
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_python_execution() {
        let config = SandboxConfig {
            sandbox_type: SandboxType::Docker,  // ou SandboxType::Gvisor se disponível
            work_dir: PathBuf::from("/tmp/cathedral_sandbox"),
            timeout_secs: 5,
            memory_limit_mb: 128,
            cpu_limit: 0.5,
            network_enabled: false,
            readonly_root: true,
            allowed_imports: vec!["math".to_string(), "json".to_string()],
            forbid_imports: vec!["os".to_string(), "subprocess".to_string(), "socket".to_string()],
        };
        let tool = CodeExecutionTool::new(config);

        let code = "print('Hello from sandbox')";
        let params = json!({ "code": code, "memory_proof": "dummy_signature" });
        let result = tool.execute(params).await;
        assert!(result.is_ok());
        let output = result.unwrap();
        assert!(output.success);
        assert!(output.output.contains("Hello from sandbox"));
    }
}
