//! LangGraph – orquestração de estados com auditoria.

use arkhe_audit_trail::{AuditTrail, NewAuditEntry, AuditCategory, AuditOutcome};
use arkhe_policy_gateway::{PolicyGateway, PolicyInput, GatewayVerdict};
use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use dashmap::DashMap;

/// Estado de um grafo.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphState {
    pub id: String,
    pub value: serde_json::Value,
    pub node: String,
    pub step: u64,
    pub metadata: HashMap<String, String>,
}

/// Definição de um nó.
#[derive(Debug, Clone)]
pub struct GraphNode {
    pub id: String,
    pub name: String,
    pub description: String,
}

/// Transição entre nós.
#[derive(Debug, Clone)]
pub struct GraphEdge {
    pub from: String,
    pub to: String,
    pub condition: Option<String>, // expressão Rego? ou função
}

/// Trait para executar um nó.
#[async_trait]
pub trait NodeExecutor: Send + Sync {
    async fn execute(&self, state: GraphState) -> Result<GraphState, String>;
}

/// LangGraph – orquestra fluxos de estado.
pub struct LangGraph {
    nodes: HashMap<String, GraphNode>,
    edges: Vec<GraphEdge>,
    current: Option<String>,
    state: DashMap<String, GraphState>,
    gateway: Arc<PolicyGateway>,
    audit: Arc<AuditTrail>,
    executors: HashMap<String, Box<dyn NodeExecutor>>,
}

impl LangGraph {
    pub fn new(gateway: Arc<PolicyGateway>, audit: Arc<AuditTrail>) -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
            current: None,
            state: DashMap::new(),
            gateway,
            audit,
            executors: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node: GraphNode, executor: Box<dyn NodeExecutor>) {
        self.nodes.insert(node.id.clone(), node);
        self.executors.insert(node.id.clone(), executor);
    }

    pub fn add_edge(&mut self, from: &str, to: &str) {
        self.edges.push(GraphEdge {
            from: from.into(),
            to: to.into(),
            condition: None,
        });
    }

    pub fn set_entry(&mut self, node_id: &str) {
        self.current = Some(node_id.into());
    }

    /// Executa o grafo passo a passo.
    pub async fn run(&mut self, initial_state: GraphState) -> Result<GraphState, String> {
        let mut current_state = initial_state;
        let mut step = 0;
        while let Some(node_id) = &self.current {
            // Verificar política
            let input = PolicyInput {
                actor_did: "langgraph".into(),
                action: format!("graph:node:{}", node_id),
                resource: "langgraph".into(),
                admin_mode: false,
                attributes: {
                    let mut m = HashMap::new();
                    m.insert("step".into(), serde_json::json!(step));
                    m
                },
            };
            let decision = self.gateway.evaluate(&input)
                .map_err(|e| e.to_string())?;
            if decision.verdict != GatewayVerdict::Allow {
                return Err(format!("Policy denied: {}", decision.reason));
            }

            // Executar nó
            let executor = self.executors.get(node_id)
                .ok_or_else(|| format!("No executor for node {}", node_id))?;
            current_state = executor.execute(current_state).await?;
            current_state.node = node_id.clone();
            current_state.step = step;
            self.state.insert(current_state.id.clone(), current_state.clone());

            // Auditar
            let mut trail = self.audit.lock().unwrap();
            let mut details = HashMap::new();
            details.insert("node".into(), serde_json::json!(node_id));
            details.insert("step".into(), serde_json::json!(step));
            let _ = trail.record(NewAuditEntry {
                category: AuditCategory::DataAccess,
                action: format!("graph:step:{}", node_id),
                actor_did: "langgraph".into(),
                resource: current_state.id.clone(),
                outcome: AuditOutcome::Success,
                details,
            });

            // Transição
            let next = self.edges.iter()
                .find(|e| e.from == *node_id)
                .map(|e| e.to.clone());
            self.current = next;
            step += 1;
        }
        Ok(current_state)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct EchoExecutor;
    #[async_trait]
    impl NodeExecutor for EchoExecutor {
        async fn execute(&self, mut state: GraphState) -> Result<GraphState, String> {
            state.value = serde_json::json!({"echo": state.value});
            Ok(state)
        }
    }

    #[tokio::test]
    async fn test_simple_graph() {
        let gateway = Arc::new(PolicyGateway::new(GatewayConfig::default()).unwrap());
        let audit = Arc::new(AuditTrail::new());
        let mut graph = LangGraph::new(gateway, audit);
        graph.add_node(
            GraphNode { id: "n1".into(), name: "echo".into(), description: "".into() },
            Box::new(EchoExecutor),
        );
        graph.set_entry("n1");
        let state = GraphState {
            id: "s1".into(),
            value: serde_json::json!("hello"),
            node: "start".into(),
            step: 0,
            metadata: HashMap::new(),
        };
        let result = graph.run(state).await.unwrap();
        assert_eq!(result.value["echo"], serde_json::json!("hello"));
    }
}
