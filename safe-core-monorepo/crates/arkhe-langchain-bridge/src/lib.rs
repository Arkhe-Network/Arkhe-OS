// crates/arkhe-langchain-bridge/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Ponte entre o Arkhe Policy Gateway e modelos LangChain.
//!
//! Este crate aplica as políticas de governança do Arkhe (Rego, WormGraph,
//! AuditTrail) ao redor de chamadas de modelo LangChain, garantindo que
//! cada inferência passe pelo pipeline de segurança.
//!
//! # Sem LangChain (modo stub)
//!
//! Quando a feature `langchain` não está ativa, o bridge usa um stub
//! que simula respostas de modelo. Útil para testar o pipeline de
//! governança sem depender do LangChain.
//!
//! # Com LangChain
//!
//! Ative com `cargo build -p arkhe-langchain-bridge --features langchain`.
//!
//! # Exemplo com admin mode
//!
//! ```
//! use arkhe_langchain_bridge::LangChainBridge;
//! use arkhe_configuration::Configuration;
//! use arkhe_policy_gateway::{PolicyGateway, GatewayConfig, PolicyInput};
//!
//! // Setup
//! let config = Configuration::new();
//! let gateway = PolicyGateway::new(GatewayConfig::default())?;
//! let bridge = LangChainBridge::new(gateway, &config);
//!
//! // Chamada com admin mode (tudo permitido, mas auditado)
//! let mut admin_config = Configuration::new();
//! admin_config.set_bool("admin_mode", true);
//! let admin_bridge = LangChainBridge::new(gateway, &admin_config);
//!
//! let result = admin_bridge.complete(
//!     "did:arkhe:admin",
//!     "Explain quantum computing",
//! ).await?;
//! ```

use arkhe_configuration::Configuration;
use arkhe_policy_gateway::{GatewayConfig, GatewayDecision, GatewayVerdict, PolicyGateway, PolicyInput};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tracing::{info, warn};

#[derive(Debug, Error)]
pub enum BridgeError {
    #[error("policy denied: {reason}")]
    PolicyDenied { reason: String },

    #[error("gateway error: {0}")]
    Gateway(#[from] arkhe_policy_gateway::GatewayError),

    #[error("model error: {0}")]
    Model(String),

    #[error("configuration error: {0}")]
    Config(String),
}

pub type BridgeResult<T> = Result<T, BridgeError>;

/// Requisição de inferência.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceRequest {
    /// DID do ator.
    pub actor_did: String,
    /// Prompt do usuário.
    pub prompt: String,
    /// Recurso being accessed (model name or endpoint).
    pub resource: String,
    /// Parâmetros extras.
    pub params: HashMap<String, serde_json::Value>,
}

/// Resposta de inferência.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResponse {
    /// Texto gerado pelo modelo.
    pub content: String,
    /// Se a requisição foi em admin mode.
    pub was_admin: bool,
    /// Decisão de política.
    pub policy_decision: GatewayDecision,
    /// Token usage estimado.
    pub input_tokens: u32,
    pub output_tokens: u32,
}

/// Trait para backends de modelo (LangChain ou stub).
#[async_trait]
pub trait ModelBackend: Send + Sync {
    /// Executa a inferência.
    async fn complete(&self, prompt: &str, params: &HashMap<String, serde_json::Value>)
        -> Result<String, String>;
}

/// Stub backend — retorna respostas simuladas.
pub struct StubBackend {
    pub response_prefix: String,
}

impl StubBackend {
    pub fn new() -> Self {
        Self {
            response_prefix: "Stub response: ".into(),
        }
    }
}

impl Default for StubBackend {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl ModelBackend for StubBackend {
    async fn complete(
        &self,
        prompt: &str,
        _params: &HashMap<String, serde_json::Value>,
    ) -> Result<String, String> {
        Ok(format!("{}{}", self.response_prefix, prompt))
    }
}

/// LangChain backend (requer feature `langchain`).
#[cfg(feature = "langchain")]
pub struct LangChainBackend {
    model_name: String,
}

#[cfg(feature = "langchain")]
impl LangChainBackend {
    pub fn new(model_name: &str) -> Self {
        Self {
            model_name: model_name.into(),
        }
    }
}

#[cfg(feature = "langchain")]
#[async_trait]
impl ModelBackend for LangChainBackend {
    async fn complete(
        &self,
        prompt: &str,
        params: &HashMap<String, serde_json::Value>,
    ) -> Result<String, String> {
        // Integração real com langchain-rust
        // NOTA: langchain-rust está em estágio inicial (v0.1.x).
        // A API pode mudar. Adaptar conforme a versão disponível.
        use langchain_rust::llms::OpenAIConfig;

        let api_key = std::env::var("OPENAI_API_KEY")
            .map_err(|_| "OPENAI_API_KEY not set".to_string())?;

        let temperature = params
            .get("temperature")
            .and_then(|v| v.as_f64())
            .unwrap_or(0.7);

        let config = OpenAIConfig::default()
            .with_api_key(&api_key)
            .with_model(&self.model_name)
            .with_temperature(temperature);

        // Chamada ao modelo via LangChain
        // (API exata depende da versão do langchain-rust)
        Err(format!(
            "LangChain integration requires langchain-rust >= 0.2. \
             Current stub: model={}, temp={}",
            self.model_name, temperature
        ))
    }
}

/// Bridge entre Arkhe governance e LangChain.
pub struct LangChainBridge {
    gateway: Arc<PolicyGateway>,
    config: Configuration,
    backend: Box<dyn ModelBackend>,
}

impl LangChainBridge {
    /// Cria bridge com stub backend.
    pub fn new(gateway: PolicyGateway, config: &Configuration) -> Self {
        Self {
            gateway: Arc::new(gateway),
            config: config.clone(),
            backend: Box::new(StubBackend::new()),
        }
    }

    /// Cria bridge com backend customizado.
    pub fn with_backend(
        gateway: PolicyGateway,
        config: &Configuration,
        backend: Box<dyn ModelBackend>,
    ) -> Self {
        Self {
            gateway: Arc::new(gateway),
            config: config.clone(),
            backend,
        }
    }

    /// Cria bridge com LangChain backend (requer feature `langchain`).
    #[cfg(feature = "langchain")]
    pub fn with_langchain(
        gateway: PolicyGateway,
        config: &Configuration,
        model_name: &str,
    ) -> Self {
        Self {
            gateway: Arc::new(gateway),
            config: config.clone(),
            backend: Box::new(LangChainBackend::new(model_name)),
        }
    }

    /// Executa inferência com checagem de política.
    pub async fn complete(&self, request: &InferenceRequest) -> BridgeResult<InferenceResponse> {
        // 1. Construir input de política
        let policy_input = PolicyInput {
            actor_did: request.actor_did.clone(),
            action: "inference".into(),
            resource: request.resource.clone(),
            admin_mode: self.config.is_admin_mode(),
            attributes: request.params.clone(),
        };

        // 2. Avaliar política
        let decision = self.gateway.evaluate(&policy_input)?;

        // 3. Se negado, retornar erro sem chamar o modelo
        if decision.verdict != GatewayVerdict::Allow {
            warn!(
                actor = %request.actor_did,
                resource = %request.resource,
                reason = %decision.reason,
                "Policy DENIED — model not called"
            );
            return Err(BridgeError::PolicyDenied {
                reason: decision.reason,
            });
        }

        // 4. Log admin mode
        if decision.is_admin_mode {
            warn!(
                actor = %request.actor_did,
                resource = %request.resource,
                "ADMIN MODE — policy bypassed, model called (audited)"
            );
        }

        // 5. Chamar o modelo
        let content = self
            .backend
            .complete(&request.prompt, &request.params)
            .await
            .map_err(BridgeError::Model)?;

        // 6. Estimar tokens (rough: 1 token ≈ 4 chars)
        let input_tokens = (request.prompt.len() as f32 / 4.0) as u32;
        let output_tokens = (content.len() as f32 / 4.0) as u32;

        info!(
            actor = %request.actor_did,
            input_tokens,
            output_tokens,
            admin = decision.is_admin_mode,
            "Inference completed"
        );

        Ok(InferenceResponse {
            content,
            was_admin: decision.is_admin_mode,
            policy_decision: decision,
            input_tokens,
            output_tokens,
        })
    }

    /// Executa inferência simples (shortcut).
    pub async fn simple_complete(
        &self,
        actor_did: &str,
        prompt: &str,
    ) -> BridgeResult<InferenceResponse> {
        self.complete(&InferenceRequest {
            actor_did: actor_did.into(),
            prompt: prompt.into(),
            resource: "default_model".into(),
            params: HashMap::new(),
        })
        .await
    }

    /// Acesso ao gateway (para consulta).
    pub fn gateway(&self) -> &PolicyGateway {
        &self.gateway
    }

    /// Acesso à configuração.
    pub fn config(&self) -> &Configuration {
        &self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use arkhe_policy_regorus::RegoPolicy;

    fn make_bridge() -> LangChainBridge {
        let gateway = PolicyGateway::new(GatewayConfig::default()).unwrap();
        let config = Configuration::new();
        LangChainBridge::new(gateway, &config)
    }

    fn make_admin_bridge() -> LangChainBridge {
        let gateway = PolicyGateway::new(GatewayConfig::default()).unwrap();
        let mut config = Configuration::new();
        config.set_bool("admin_mode", true);
        LangChainBridge::new(gateway, &config)
    }

    fn make_allowed_bridge() -> LangChainBridge {
        let policy = RegoPolicy::from_rego_text(
            "allow_read",
            r#"package arkhe.policy
default allow = false
allow { input.action == "inference" }"#,
        )
        .unwrap();

        let gateway = PolicyGateway::with_policies(
            GatewayConfig::default(),
            vec![policy],
        )
        .unwrap();

        let config = Configuration::new();
        LangChainBridge::new(gateway, &config)
    }

    #[tokio::test]
    async fn normal_mode_denied_by_default() {
        let bridge = make_bridge();
        let result = bridge.simple_complete("did:arkhe:user", "hello").await;
        assert!(matches!(result, Err(BridgeError::PolicyDenied { .. })));
    }

    #[tokio::test]
    async fn admin_mode_allows() {
        let bridge = make_admin_bridge();
        let result = bridge.simple_complete("did:arkhe:admin", "hello").await;
        assert!(result.is_ok());
        let resp = result.unwrap();
        assert!(resp.was_admin);
        assert!(resp.content.contains("hello"));
    }

    #[tokio::test]
    async fn policy_allows_inference() {
        let bridge = make_allowed_bridge();
        let result = bridge.simple_complete("did:arkhe:user", "hello").await;
        assert!(result.is_ok());
        assert!(!result.unwrap().was_admin);
    }

    #[tokio::test]
    async fn token_estimation() {
        let bridge = make_admin_bridge();
        let prompt = "a".repeat(400); // ~100 tokens
        let result = bridge.simple_complete("did:arkhe:admin", &prompt).await.unwrap();
        assert!(result.input_tokens >= 90);
        assert!(result.input_tokens <= 110);
    }

    #[tokio::test]
    async fn policy_decision_in_response() {
        let bridge = make_admin_bridge();
        let result = bridge.simple_complete("did:arkhe:admin", "test").await.unwrap();
        assert_eq!(result.policy_decision.verdict, GatewayVerdict::Allow);
        assert!(result.policy_decision.reason.contains("Admin mode"));
    }

    #[tokio::test]
    async fn custom_backend() {
        struct EchoBackend;
        #[async_trait]
        impl ModelBackend for EchoBackend {
            async fn complete(&self, prompt: &str, _: &HashMap<String, serde_json::Value>) -> Result<String, String> {
                Ok(format!("ECHO: {}", prompt))
            }
        }

        let gateway = PolicyGateway::new(GatewayConfig::default()).unwrap();
        let mut config = Configuration::new();
        config.set_bool("admin_mode", true);
        let bridge = LangChainBridge::with_backend(
            gateway,
            &config,
            Box::new(EchoBackend),
        );

        let result = bridge.simple_complete("did:arkhe:admin", "test").await.unwrap();
        assert_eq!(result.content, "ECHO: test");
    }

    #[tokio::test]
    async fn full_request_with_params() {
        let bridge = make_admin_bridge();
        let mut params = HashMap::new();
        params.insert("temperature".into(), serde_json::json!(0.5));

        let result = bridge.complete(&InferenceRequest {
            actor_did: "did:arkhe:admin".into(),
            prompt: "test".into(),
            resource: "gpt-4".into(),
            params,
        }).await.unwrap();

        assert_eq!(result.policy_decision.verdict, GatewayVerdict::Allow);
        assert!(result.was_admin);
    }
}
