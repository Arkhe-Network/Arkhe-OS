//! Vector store com aplicação de políticas de acesso.

#![warn(missing_docs)]
#![deny(unsafe_code)]

mod traits;
mod memory;
#[cfg(feature = "sqlite")]
mod sqlite;
#[cfg(feature = "qdrant")]
mod qdrant;

pub use traits::*;
pub use memory::MemoryVectorStore;
#[cfg(feature = "sqlite")]
pub use sqlite::SqliteVectorStore;
#[cfg(feature = "qdrant")]
pub use qdrant::QdrantVectorStore;

use arkhe_policy_gateway::{PolicyGateway, PolicyInput, GatewayVerdict};
use arkhe_audit_trail::{AuditTrail, NewAuditEntry, AuditCategory, AuditOutcome};
use std::collections::HashMap;
use std::sync::Arc;

/// Erros do vector store.
#[derive(Debug, thiserror::Error)]
pub enum VectorStoreError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("io: {0}")]
    Io(#[from] std::io::Error),
    #[error("serialization: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("policy denied: {reason}")]
    PolicyDenied { reason: String },
    #[error("gateway error: {0}")]
    Gateway(#[from] arkhe_policy_gateway::GatewayError),
    #[error("store error: {0}")]
    Store(String),
}

pub type VectorStoreResult<T> = Result<T, VectorStoreError>;

/// Ponto de entrada com metadados.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VectorPoint {
    pub id: String,
    pub vector: Vec<f32>,
    pub payload: HashMap<String, serde_json::Value>,
    pub metadata: HashMap<String, String>,
}

/// Operações permitidas no vector store.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VectorOp {
    Insert,
    Search,
    Delete,
    Get,
}

impl std::fmt::Display for VectorOp {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Insert => write!(f, "insert"),
            Self::Search => write!(f, "search"),
            Self::Delete => write!(f, "delete"),
            Self::Get => write!(f, "get"),
        }
    }
}

/// Trait para armazenamento vetorial.
#[async_trait::async_trait]
pub trait VectorStore: Send + Sync {
    /// Insere um vetor com payload.
    async fn insert(&self, point: VectorPoint) -> VectorStoreResult<()>;

    /// Busca os K vetores mais próximos.
    async fn search(
        &self,
        vector: &[f32],
        limit: usize,
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> VectorStoreResult<Vec<VectorPoint>>;

    /// Obtém um ponto por ID.
    async fn get(&self, id: &str) -> VectorStoreResult<VectorPoint>;

    /// Remove um ponto por ID.
    async fn delete(&self, id: &str) -> VectorStoreResult<()>;

    /// Lista todos os IDs.
    async fn list_ids(&self) -> VectorStoreResult<Vec<String>>;
}

/// Vector store com governança via PolicyGateway.
pub struct GovernedVectorStore<S: VectorStore> {
    inner: S,
    gateway: Arc<PolicyGateway>,
    audit_trail: Arc<AuditTrail>,
    collection: String,
}

impl<S: VectorStore> GovernedVectorStore<S> {
    pub fn new(
        inner: S,
        gateway: Arc<PolicyGateway>,
        audit_trail: Arc<AuditTrail>,
        collection: &str,
    ) -> Self {
        Self {
            inner,
            gateway,
            audit_trail,
            collection: collection.into(),
        }
    }

    async fn check_policy(
        &self,
        actor: &str,
        op: VectorOp,
        resource: &str,
    ) -> VectorStoreResult<()> {
        let input = PolicyInput {
            actor_did: actor.into(),
            action: format!("vector:{}", op),
            resource: format!("{}/{}", self.collection, resource),
            admin_mode: false, // será preenchido pelo gateway
            attributes: {
                let mut m = HashMap::new();
                m.insert("collection".into(), serde_json::json!(self.collection));
                m
            },
        };

        let decision = self.gateway.evaluate(&input)?;
        if decision.verdict != GatewayVerdict::Allow {
            return Err(VectorStoreError::PolicyDenied {
                reason: decision.reason,
            });
        }
        Ok(())
    }

    async fn audit(
        &self,
        actor: &str,
        op: VectorOp,
        resource: &str,
        outcome: AuditOutcome,
        details: HashMap<String, serde_json::Value>,
    ) {
        let mut trail = self.audit_trail.lock().unwrap();
        let _ = trail.record(NewAuditEntry {
            category: AuditCategory::DataAccess,
            action: format!("vector:{}", op),
            actor_did: actor.into(),
            resource: format!("{}/{}", self.collection, resource),
            outcome,
            details,
        });
    }
}

#[async_trait::async_trait]
impl<S: VectorStore> VectorStore for GovernedVectorStore<S> {
    async fn insert(&self, point: VectorPoint) -> VectorStoreResult<()> {
        self.check_policy("system", VectorOp::Insert, &point.id).await?;
        self.inner.insert(point.clone()).await?;
        self.audit("system", VectorOp::Insert, &point.id, AuditOutcome::Success, {
            let mut d = HashMap::new();
            d.insert("id".into(), serde_json::json!(point.id));
            d
        }).await;
        Ok(())
    }

    async fn search(
        &self,
        vector: &[f32],
        limit: usize,
        filter: Option<HashMap<String, serde_json::Value>>,
    ) -> VectorStoreResult<Vec<VectorPoint>> {
        // Para busca, usamos um recurso genérico
        self.check_policy("system", VectorOp::Search, "search").await?;
        let results = self.inner.search(vector, limit, filter).await?;
        self.audit("system", VectorOp::Search, "search", AuditOutcome::Success, {
            let mut d = HashMap::new();
            d.insert("limit".into(), serde_json::json!(limit));
            d.insert("results".into(), serde_json::json!(results.len()));
            d
        }).await;
        Ok(results)
    }

    async fn get(&self, id: &str) -> VectorStoreResult<VectorPoint> {
        self.check_policy("system", VectorOp::Get, id).await?;
        let point = self.inner.get(id).await?;
        self.audit("system", VectorOp::Get, id, AuditOutcome::Success, {
            let mut d = HashMap::new();
            d.insert("id".into(), serde_json::json!(id));
            d
        }).await;
        Ok(point)
    }

    async fn delete(&self, id: &str) -> VectorStoreResult<()> {
        self.check_policy("system", VectorOp::Delete, id).await?;
        self.inner.delete(id).await?;
        self.audit("system", VectorOp::Delete, id, AuditOutcome::Success, {
            let mut d = HashMap::new();
            d.insert("id".into(), serde_json::json!(id));
            d
        }).await;
        Ok(())
    }

    async fn list_ids(&self) -> VectorStoreResult<Vec<String>> {
        // Apenas leitura, sem política específica
        self.inner.list_ids().await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use arkhe_policy_gateway::{GatewayConfig, PolicyGateway};
    use arkhe_policy_regorus::{PolicyEngine, RegoPolicy};

    fn make_gateway() -> Arc<PolicyGateway> {
        let policy = RegoPolicy::from_rego_text(
            "allow_vector_search",
            r#"package arkhe.policy
default allow = false
allow { input.action == "vector:search" }
allow { input.admin_mode == true }
"#,
        ).unwrap();
        let mut g = PolicyGateway::new(GatewayConfig::default()).unwrap();
        g.add_policy(policy).unwrap();
        Arc::new(g)
    }

    #[tokio::test]
    async fn test_insert_denied_by_default() {
        let store = MemoryVectorStore::new();
        let gateway = make_gateway();
        let audit = Arc::new(AuditTrail::new());
        let governed = GovernedVectorStore::new(store, gateway, audit, "test");

        let point = VectorPoint {
            id: "p1".into(),
            vector: vec![1.0, 0.0],
            payload: HashMap::new(),
            metadata: HashMap::new(),
        };
        let result = governed.insert(point).await;
        assert!(matches!(result, Err(VectorStoreError::PolicyDenied { .. })));
    }

    #[tokio::test]
    async fn test_search_allowed() {
        let store = MemoryVectorStore::new();
        let gateway = make_gateway();
        let audit = Arc::new(AuditTrail::new());
        let governed = GovernedVectorStore::new(store, gateway, audit, "test");

        let results = governed.search(&[1.0, 0.0], 10, None).await;
        assert!(results.is_ok());
    }
}
