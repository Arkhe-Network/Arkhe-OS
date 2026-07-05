// crates/arkhe-agi-coordinator/src/integration_example.rs
// Este arquivo NÃO faz parte do crate — é documentação de padrão de uso.

//! # Padrão de Integração: AgiCoordinator + PolicyGateway
//!
//! O AgiCoordinator existente não conhece o PolicyGateway. Em vez de
//! modificá-lo (o que quebraria backward compat), usamos um wrapper
//! que aplica governança antes de delegar ao coordinator.

use arkhe_configuration::Configuration;
use arkhe_langchain_bridge::{BridgeError, InferenceRequest, InferenceResponse, LangChainBridge};
use arkhe_policy_gateway::{GatewayConfig, PolicyGateway};

/// Agente com governança — wrapper em torno do AgiCoordinator.
///
/// Em produção, substitua `LangChainBridge` pelo seu coordinator real.
pub struct GovernedAgent {
    /// Bridge que aplica políticas antes de chamar o modelo.
    bridge: LangChainBridge,
    /// DID do agente.
    did: String,
}

impl GovernedAgent {
    /// Cria agente com governança.
    pub fn new(did: &str, config: &Configuration) -> Result<Self, arkhe_policy_gateway::GatewayError> {
        let gateway = PolicyGateway::new(GatewayConfig::default())?;
        let bridge = LangChainBridge::new(gateway, config);

        Ok(Self {
            bridge,
            did: did.into(),
        }
    }

    /// Cria agente com admin mode (para desenvolvimento).
    pub fn new_admin(did: &str) -> Result<Self, arkhe_policy_gateway::GatewayError> {
        let mut config = Configuration::new();
        config.set_bool("admin_mode", true);

        let gateway = PolicyGateway::new(GatewayConfig::default())?;
        let bridge = LangChainBridge::new(gateway, &config);

        Ok(Self {
            bridge,
            did: did.into(),
        })
    }

    /// Processa uma mensagem do usuário.
    pub async fn process(&self, prompt: &str) -> Result<String, BridgeError> {
        let response = self.bridge.complete(&InferenceRequest {
            actor_did: self.did.clone(),
            prompt: prompt.into(),
            resource: "default".into(),
            params: std::collections::HashMap::new(),
        }).await?;

        if response.was_admin {
            tracing::warn!(
                did = %self.did,
                "Admin action completed (audited in WormGraph + AuditTrail)"
            );
        }

        Ok(response.content)
    }

    /// Processa com recurso específico (para routing).
    pub async fn process_with_resource(
        &self,
        prompt: &str,
        resource: &str,
    ) -> Result<String, BridgeError> {
        let response = self.bridge.complete(&InferenceRequest {
            actor_did: self.did.clone(),
            prompt: prompt.into(),
            resource: resource.into(),
            params: std::collections::HashMap::new(),
        }).await?;

        Ok(response.content)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn admin_agent_can_process() {
        let agent = GovernedAgent::new_admin("did:arkhe:admin").unwrap();
        let result = agent.process("Hello").await;
        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn normal_agent_denied_without_policy() {
        let agent = GovernedAgent::new("did:arkhe:user", &Configuration::new()).unwrap();
        let result = agent.process("Hello").await;
        assert!(result.is_err());
    }
}
