//! Gates de segurança para execução de ferramentas

use serde_json::Value;

/// Gate de segurança para chamadas de ferramentas.
#[derive(Debug, Clone)]
pub struct SecurityGate {
    /// Schemes HTTP permitidos (ex: ["https"])
    pub allowed_schemes: Vec<String>,
    /// Domínios permitidos (vazio = todos)
    pub allowed_domains: Vec<String>,
    /// Tamanho máximo de resposta em bytes
    pub max_response_size: usize,
    /// Timeout em segundos
    pub timeout_secs: u64,
    /// Binários permitidos para execução shell
    pub allowed_binaries: Vec<String>,
    /// Diretórios permitidos para leitura (Landlock)
    pub read_paths: Vec<std::path::PathBuf>,
    /// Diretórios permitidos para escrita (Landlock)
    pub write_paths: Vec<std::path::PathBuf>,
}

impl Default for SecurityGate {
    fn default() -> Self {
        Self {
            allowed_schemes: vec!["https".into()],
            allowed_domains: vec![],
            max_response_size: 10 * 1024 * 1024, // 10MB
            timeout_secs: 30,
            allowed_binaries: vec![
                "python3".into(),
                "python3.11".into(),
                "python3.12".into(),
                "rustc".into(),
                "bash".into(),
                "sh".into(),
            ],
            read_paths: vec!["/usr".into(), "/lib".into(), "/lib64".into()],
            write_paths: vec![],
        }
    }
}

/// Gate de execução específico para uma tarefa.
#[derive(Debug, Clone)]
pub struct ExecutionGate {
    pub security: SecurityGate,
    pub workspace: std::path::PathBuf,
    pub enable_landlock: bool,
    pub enable_timeout: bool,
}

impl ExecutionGate {
    pub fn new(security: SecurityGate, workspace: std::path::PathBuf) -> Self {
        Self {
            security,
            workspace,
            enable_landlock: true,
            enable_timeout: true,
        }
    }

    /// Valida uma URL contra as regras do gate.
    pub fn validate_url(&self, url: &str) -> Result<url::Url, crate::error::ExecError> {
        let parsed = url::Url::parse(url)
            .map_err(|e| crate::error::ExecError::InvalidUrl(e.to_string()))?;

        let scheme = parsed.scheme();
        if !self.security.allowed_schemes.contains(&scheme.to_string()) {
            return Err(crate::error::ExecError::ForbiddenScheme(scheme.to_string()));
        }

        if let Some(domain) = parsed.host_str() {
            if !self.security.allowed_domains.is_empty()
                && !self.security.allowed_domains.contains(&domain.to_string()) {
                return Err(crate::error::ExecError::ForbiddenDomain(domain.to_string()));
            }
        }

        Ok(parsed)
    }

    /// Valida um binário contra a whitelist.
    pub fn validate_binary(&self, binary: &str) -> Result<(), crate::error::ExecError> {
        // Extrair apenas o nome do binário (sem path)
        let name = std::path::Path::new(binary)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or(binary);

        if !self.security.allowed_binaries.contains(&name.to_string()) {
            return Err(crate::error::ExecError::BinaryNotAllowed(name.to_string()));
        }
        Ok(())
    }
}
