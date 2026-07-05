// crates/arkhe-governance/src/capability.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityToken {
    pub token_id: String,
    pub subject: String,
    pub actions: Vec<String>,
    pub resources: Vec<String>,
    pub expires_at: Option<chrono::DateTime<chrono::Utc>>,
}

impl CapabilityToken {
    pub fn can(&self, action: &str, resource: &str) -> bool {
        self.actions.iter().any(|a| a == action)
            && self.resources.iter().any(|r| r == resource)
    }
}
