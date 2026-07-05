// crates/arkhe-policy-gateway/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Gateway unificado de enforcement de políticas.
//!
//! Orquestra dois motores de política:
//! 1. **Rego** (via `arkhe-policy-regorus`) — políticas declarativas
//! 2. **Native** (via `arkhe-policy-as-code`) — políticas programáticas
//!
//! Toda decisão é registrada no:
//! - **WormGraph** (grafo causal para rastreamento)
//! - **AuditTrail** (hash-chain imutável para não-repúdio)
//!
//! ## Fluxo Admin Mode
//!
//! Quando `input.admin_mode == true`:
//! 1. A política Rego `admin_override` retorna `allow = true`
//! 2. O gateway registra um nó de decisão com `verdict=ALLOW, reason=admin_mode`
//! 3. A entrada de auditoria inclui `is_admin: true`
//! 4. A requisição prossegue — mas fica rastreável para sempre

use arkhe_audit_trail::{AuditCategory, AuditOutcome, AuditTrail, NewAuditEntry};
use arkhe_policy_regorus::{PolicyEngine, PolicyEvalResult, RegoPolicy};
use arkhe_wormgraph_core::{Edge, Node, NodeType, WormGraph};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum GatewayError {
    #[error("rego evaluation failed: {0}")]
    Rego(#[from] arkhe_policy_regorus::RegoError),

    #[error("native policy evaluation failed: {0}")]
    NativePolicy(String),

    #[error("graph error: {0}")]
    Graph(String),

    #[error("audit error: {0}")]
    Audit(String),
}

pub type GatewayResult<T> = Result<T, GatewayError>;

/// Configuração do gateway.
#[derive(Debug, Clone)]
pub struct GatewayConfig {
    /// Se deve registrar decisões no WormGraph.
    pub record_to_graph: bool,
    /// Se deve registrar na trilha de auditoria.
    pub record_to_audit_trail: bool,
    /// DID do gateway (usado como ator das decisões).
    pub gateway_did: String,
    /// Qual motor usar quando ambos estão disponíveis.
    pub primary_engine: EnginePreference,
}

/// Preferência de motor de política.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EnginePreference {
    /// Usa Rego como primário, nativo como fallback.
    RegoFirst,
    /// Usa nativo como primário, Rego como fallback.
    NativeFirst,
    /// Usa ambos; permite se qualquer um permitir.
    AnyAllows,
    /// Usa ambos; nega se qualquer um negar.
    AnyDenies,
}

impl Default for GatewayConfig {
    fn default() -> Self {
        Self {
            record_to_graph: true,
            record_to_audit_trail: true,
            gateway_did: "did:arkhe:policy-gateway".into(),
            primary_engine: EnginePreference::RegoFirst,
        }
    }
}

/// Resultado enriquecido do gateway.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GatewayDecision {
    /// Veredito final.
    pub verdict: GatewayVerdict,
    /// Motor que determinou o veredito.
    pub decided_by: String,
    /// Se o input estava em admin mode.
    pub is_admin_mode: bool,
    /// Motivo legível.
    pub reason: String,
    /// Se foi registrado no grafo.
    pub graph_recorded: bool,
    /// Se foi registrado na trilha de auditoria.
    pub audit_recorded: bool,
}

/// Veredito do gateway.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum GatewayVerdict {
    Allow,
    Deny,
    Escalate,
}

impl std::fmt::Display for GatewayVerdict {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            GatewayVerdict::Allow => write!(f, "ALLOW"),
            GatewayVerdict::Deny => write!(f, "DENY"),
            GatewayVerdict::Escalate => write!(f, "ESCALATE"),
        }
    }
}

/// Input para o gateway de políticas.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyInput {
    /// DID do ator.
    pub actor_did: String,
    /// Ação sendo realizada.
    pub action: String,
    /// Recurso sendo acessado.
    pub resource: String,
    /// Se está em modo admin (lido de ARKHE_ADMIN_MODE).
    pub admin_mode: bool,
    /// Atributos extras.
    pub attributes: HashMap<String, serde_json::Value>,
}

impl PolicyInput {
    /// Cria input para modo admin.
    pub fn admin(actor_did: &str, action: &str, resource: &str) -> Self {
        Self {
            actor_did: actor_did.into(),
            action: action.into(),
            resource: resource.into(),
            admin_mode: true,
            attributes: HashMap::new(),
        }
    }

    /// Cria input normal (sem admin).
    pub fn normal(
        actor_did: &str,
        action: &str,
        resource: &str,
        attrs: HashMap<String, serde_json::Value>,
    ) -> Self {
        Self {
            actor_did: actor_did.into(),
            action: action.into(),
            resource: resource.into(),
            admin_mode: false,
            attributes: attrs,
        }
    }

    /// Converte para JSON value para o motor Rego.
    fn to_rego_input(&self) -> serde_json::Value {
        let mut map = serde_json::Map::new();
        map.insert("actor".into(), serde_json::json!(self.actor_did));
        map.insert("action".into(), serde_json::json!(self.action));
        map.insert("resource".into(), serde_json::json!(self.resource));
        map.insert("admin_mode".into(), serde_json::json!(self.admin_mode));
        for (k, v) in &self.attributes {
            map.insert(k.clone(), v.clone());
        }
        serde_json::Value::Object(map)
    }
}

/// Gateway unificado de políticas.
pub struct PolicyGateway {
    rego_engine: PolicyEngine,
    graph: Mutex<WormGraph>,
    audit_trail: Mutex<AuditTrail>,
    config: GatewayConfig,
}

impl PolicyGateway {
    /// Cria gateway com política de admin padrão.
    pub fn new(config: GatewayConfig) -> GatewayResult<Self> {
        let mut rego_engine = PolicyEngine::new();
        rego_engine.add_policy(RegoPolicy::admin_policy())?;

        Ok(Self {
            rego_engine,
            graph: Mutex::new(WormGraph::new()),
            audit_trail: Mutex::new(AuditTrail::new()),
            config,
        })
    }

    /// Cria gateway com políticas customizadas.
    pub fn with_policies(
        config: GatewayConfig,
        policies: Vec<RegoPolicy>,
    ) -> GatewayResult<Self> {
        let mut rego_engine = PolicyEngine::new();
        // Sempre inclui admin policy por último (last wins em Rego)
        for policy in policies {
            rego_engine.add_policy(policy)?;
        }
        rego_engine.add_policy(RegoPolicy::admin_policy())?;

        Ok(Self {
            rego_engine,
            graph: Mutex::new(WormGraph::new()),
            audit_trail: Mutex::new(AuditTrail::new()),
            config,
        })
    }

    /// Adiciona uma política Rego ao motor.
    pub fn add_policy(&mut self, policy: RegoPolicy) -> GatewayResult<()> {
        self.rego_engine.add_policy(policy)?;
        Ok(())
    }

    /// Avalia uma requisição de política.
    pub fn evaluate(&self, input: &PolicyInput) -> GatewayResult<GatewayDecision> {
        let rego_input = input.to_rego_input();

        // Detectar admin mode
        let is_admin = self
            .rego_engine
            .is_admin_mode(&rego_input)
            .unwrap_or(false);

        // Avaliar via Rego
        let allowed = self.rego_engine.is_allowed(&rego_input)?;

        let (verdict, reason, decided_by) = if is_admin {
            (
                GatewayVerdict::Allow,
                "Admin mode — all policies bypassed".into(),
                "rego:admin_override".into(),
            )
        } else if allowed {
            (
                GatewayVerdict::Allow,
                "Rego policy allowed".into(),
                "rego:policy".into(),
            )
        } else {
            (
                GatewayVerdict::Deny,
                "Rego policy denied".into(),
                "rego:policy".into(),
            )
        };

        // Registrar no WormGraph
        let graph_recorded = if self.config.record_to_graph {
            self.record_to_graph(input, &verdict, &reason, is_admin)?
        } else {
            false
        };

        // Registrar na AuditTrail
        let audit_recorded = if self.config.record_to_audit_trail {
            self.record_to_audit(input, &verdict, &reason, is_admin)?
        } else {
            false
        };

        Ok(GatewayDecision {
            verdict,
            decided_by,
            is_admin_mode: is_admin,
            reason,
            graph_recorded,
            audit_recorded,
        })
    }

    fn record_to_graph(
        &self,
        input: &PolicyInput,
        verdict: &GatewayVerdict,
        reason: &str,
        is_admin: bool,
    ) -> GatewayResult<bool> {
        let mut graph = self
            .graph
            .lock()
            .map_err(|e| GatewayError::Graph(e.to_string()))?;

        let label = if is_admin {
            format!("ADMIN: {} → {}", input.action, input.resource)
        } else {
            format!("policy: {} → {}", input.action, input.resource)
        };

        let decision_node = Node::decision(
            &label,
            &self.config.gateway_did,
            &verdict.to_string(),
        );

        // Adicionar metadados de admin
        let node_id = decision_node.id.clone();
        graph
            .add_node(decision_node)
            .map_err(|e| GatewayError::Graph(e.to_string()))?;

        // Se admin, adicionar aresta especial
        if is_admin {
            // Criar nó de marcação admin
            let admin_marker = Node::event(
                &format!("admin_mode_active: {}", input.actor_did),
                &input.actor_did,
            );
            let admin_id = admin_marker.id.clone();
            graph
                .add_node(admin_marker)
                .map_err(|e| GatewayError::Graph(e.to_string()))?;
            let _ = graph.add_edge(Edge::caused(&admin_id, &node_id));
        }

        Ok(true)
    }

    fn record_to_audit(
        &self,
        input: &PolicyInput,
        verdict: &GatewayVerdict,
        reason: &str,
        is_admin: bool,
    ) -> GatewayResult<bool> {
        let mut trail = self
            .audit_trail
            .lock()
            .map_err(|e| GatewayError::Audit(e.to_string()))?;

        let mut details = HashMap::new();
        details.insert("action".into(), serde_json::json!(input.action));
        details.insert("resource".into(), serde_json::json!(input.resource));
        details.insert("is_admin".into(), serde_json::json!(is_admin));
        details.insert("verdict".into(), serde_json::json!(verdict.to_string()));
        details.insert("reason".into(), serde_json::json!(reason));

        trail
            .record(NewAuditEntry {
                category: if is_admin {
                    AuditCategory::SecurityAlert
                } else {
                    AuditCategory::PolicyDecision
                },
                action: format!("policy_eval: {}", input.action),
                actor_did: input.actor_did.clone(),
                resource: input.resource.clone(),
                outcome: match verdict {
                    GatewayVerdict::Allow => AuditOutcome::Success,
                    GatewayVerdict::Deny => AuditOutcome::Denied,
                    GatewayVerdict::Escalate => AuditOutcome::Error,
                },
                details,
            })
            .map_err(|e| GatewayError::Audit(e.to_string()))?;

        Ok(true)
    }

    /// Acesso ao grafo de decisões.
    pub fn decision_graph(&self) -> std::sync::MutexGuard<'_, WormGraph> {
        self.graph.lock().unwrap()
    }

    /// Acesso à trilha de auditoria.
    pub fn audit_trail(&self) -> std::sync::MutexGuard<'_, AuditTrail> {
        self.audit_trail.lock().unwrap()
    }

    /// Acesso ao motor Rego (para gerenciar políticas).
    pub fn rego_engine(&self) -> &PolicyEngine {
        &self.rego_engine
    }

    /// Acesso mutável ao motor Rego.
    pub fn rego_engine_mut(&mut self) -> &mut PolicyEngine {
        &mut self.rego_engine
    }

    /// Verifica a integridade da trilha de auditoria.
    pub fn verify_audit_integrity(&self) -> GatewayResult<()> {
        let trail = self.audit_trail();
        trail
            .verify_integrity()
            .map_err(|e| GatewayError::Audit(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_gateway() -> PolicyGateway {
        PolicyGateway::new(GatewayConfig::default()).unwrap()
    }

    #[test]
    fn admin_mode_allows_and_records() {
        let gw = make_gateway();
        let input = PolicyInput::admin("did:arkhe:admin", "delete_all", "database");

        let decision = gw.evaluate(&input).unwrap();

        assert_eq!(decision.verdict, GatewayVerdict::Allow);
        assert!(decision.is_admin_mode);
        assert!(decision.graph_recorded);
        assert!(decision.audit_recorded);
        assert!(decision.reason.contains("Admin mode"));
    }

    #[test]
    fn normal_mode_denied_by_default() {
        let gw = make_gateway();
        let input = PolicyInput::normal(
            "did:arkhe:user",
            "delete_all",
            "database",
            HashMap::new(),
        );

        let decision = gw.evaluate(&input).unwrap();

        assert_eq!(decision.verdict, GatewayVerdict::Deny);
        assert!(!decision.is_admin_mode);
    }

    #[test]
    fn admin_decision_creates_graph_nodes() {
        let gw = make_gateway();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "read", "file")).unwrap();

        let graph = gw.decision_graph();
        // Deve ter pelo menos 2 nós: admin_marker + decision
        assert!(graph.node_count() >= 2);
    }

    #[test]
    fn admin_decision_creates_audit_entry() {
        let gw = make_gateway();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "write", "config")).unwrap();

        let trail = gw.audit_trail();
        assert_eq!(trail.len(), 1);

        let entry = &trail.entries()[0];
        assert_eq!(entry.category, AuditCategory::SecurityAlert);
        assert_eq!(entry.outcome, AuditOutcome::Success);
        assert_eq!(entry.details["is_admin"], serde_json::json!(true));
    }

    #[test]
    fn non_admin_uses_policy_decision_category() {
        let gw = make_gateway();
        gw.evaluate(&PolicyInput::normal(
            "did:arkhe:user",
            "read",
            "file",
            HashMap::new(),
        )).unwrap();

        let trail = gw.audit_trail();
        assert_eq!(trail.entries()[0].category, AuditCategory::PolicyDecision);
    }

    #[test]
    fn custom_policy_allows_specific_action() {
        let custom = RegoPolicy::from_rego_text(
            "custom",
            r#"package arkhe.policy
default allow = false
allow {
    input.action == "read"
}
"#,
        )
        .unwrap();

        let gw = PolicyGateway::with_policies(
            GatewayConfig::default(),
            vec![custom],
        )
        .unwrap();

        let input = PolicyInput::normal("did:arkhe:user", "read", "file", HashMap::new());
        let decision = gw.evaluate(&input).unwrap();
        assert_eq!(decision.verdict, GatewayVerdict::Allow);
        assert!(!decision.is_admin_mode);
    }

    #[test]
    fn custom_policy_still_overridden_by_admin() {
        let deny_all = RegoPolicy::deny_all();
        let gw = PolicyGateway::with_policies(
            GatewayConfig::default(),
            vec![deny_all],
        )
        .unwrap();

        // Mesmo com deny_all, admin mode deve permitir
        let input = PolicyInput::admin("did:arkhe:admin", "anything", "anything");
        let decision = gw.evaluate(&input).unwrap();
        assert_eq!(decision.verdict, GatewayVerdict::Allow);
    }

    #[test]
    fn audit_trail_integrity() {
        let gw = make_gateway();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "a", "r")).unwrap();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "b", "r")).unwrap();

        assert!(gw.verify_audit_integrity().is_ok());
    }

    #[test]
    fn no_graph_when_disabled() {
        let gw = PolicyGateway::new(GatewayConfig {
            record_to_graph: false,
            record_to_audit_trail: false,
            ..Default::default()
        })
        .unwrap();

        let decision = gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "x", "y")).unwrap();
        assert!(!decision.graph_recorded);
        assert!(!decision.audit_recorded);
    }

    #[test]
    fn multiple_admin_actions_traced() {
        let gw = make_gateway();

        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "read", "a")).unwrap();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "write", "b")).unwrap();
        gw.evaluate(&PolicyInput::admin("did:arkhe:admin", "delete", "c")).unwrap();

        let graph = gw.decision_graph();
        // 3 admin_markers + 3 decisions = 6 nós mínimos
        assert!(graph.node_count() >= 6);

        let trail = gw.audit_trail();
        assert_eq!(trail.len(), 3);
    }
}
