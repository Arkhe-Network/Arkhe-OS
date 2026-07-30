use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EnforceResponse {
    pub allowed: bool,
    pub result: Option<serde_json::Value>,
    pub request_id: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViolationsResponse {
    pub total: usize,
    pub violations: Vec<ViolationView>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ViolationView {
    pub constraint_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvariantsResponse {
    pub total: usize,
    pub invariants: Vec<InvariantView>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvariantView {
    pub id: String,
    pub severity: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
    pub components: HealthComponents,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthComponents {
    pub ethics_engine: String,
    pub invariants: String,
    pub total_constraints: usize,
    pub total_invariants: usize,
}
