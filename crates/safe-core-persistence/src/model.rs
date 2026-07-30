use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoredRule {
    pub id: String,
    pub action: String,
    pub constraint_text: String,
    pub severity: String,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoredWorkflow {
    pub id: String,
    pub spec: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoredMetric {
    pub id: i64,
    pub metrics_json: String,
}
