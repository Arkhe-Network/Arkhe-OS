use std::sync::Arc;
use tokio::sync::RwLock;

pub struct EthicsEngineMock {
    pub constraints: usize,
    pub violations: RwLock<Vec<crate::api::ViolationView>>,
}

impl EthicsEngineMock {
    pub fn new() -> Self {
        Self {
            constraints: 4,
            violations: RwLock::new(Vec::new()),
        }
    }

    pub async fn check_action(&self, action: &str, context: &serde_json::Value) -> Result<EthicsResultMock, safe_core_ethics::EthicsError> {
        if let Some(harm) = context.get("harm_to_humans").and_then(|v| v.as_bool()) {
            if harm {
                self.violations.write().await.push(crate::api::ViolationView { constraint_id: "ETH-001".into() });
                return Ok(EthicsResultMock { allowed: false, type_: "blocked".into() });
            }
        }

        if action == "opaque" {
            return Ok(EthicsResultMock { allowed: false, type_: "requires_approval".into() });
        }

        Ok(EthicsResultMock { allowed: true, type_: "allowed".into() })
    }

    pub async fn get_violations(&self) -> Vec<crate::api::ViolationView> {
        self.violations.read().await.clone()
    }

    pub async fn clear_violations(&self) {
        self.violations.write().await.clear();
    }

    pub async fn constraint_count(&self) -> usize {
        self.constraints
    }
}

pub struct EthicsResultMock {
    allowed: bool,
    type_: String,
}

impl EthicsResultMock {
    pub fn is_allowed(&self) -> bool {
        self.allowed
    }
}

impl From<&EthicsResultMock> for serde_json::Value {
    fn from(val: &EthicsResultMock) -> Self {
        serde_json::json!({
            "type": val.type_
        })
    }
}

pub struct BridgeState {
    pub ethics_engine: Arc<EthicsEngineMock>,
    pub invariants: Vec<crate::api::InvariantView>,
}

impl Default for BridgeState {
    fn default() -> Self {
        Self::new()
    }
}

impl BridgeState {
    pub fn new() -> Self {
        Self {
            ethics_engine: Arc::new(EthicsEngineMock::new()),
            invariants: vec![
                crate::api::InvariantView { id: "INV-001".into(), severity: "Critical".into() },
                crate::api::InvariantView { id: "INV-002".into(), severity: "High".into() },
                crate::api::InvariantView { id: "INV-003".into(), severity: "Medium".into() },
                crate::api::InvariantView { id: "INV-004".into(), severity: "Low".into() },
                crate::api::InvariantView { id: "INV-005".into(), severity: "Info".into() },
            ],
        }
    }
}
