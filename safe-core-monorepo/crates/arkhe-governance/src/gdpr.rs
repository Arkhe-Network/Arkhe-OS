// crates/arkhe-governance/src/gdpr.rs
use arkhe_core::ArkheHash;
use arkhe_identity::ArkheDid;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RightToErasure {
    pub subject: ArkheDid,
    pub request_id: String,
    pub requested_at: DateTime<Utc>,
    pub status: ErasureStatus,
    pub tombstoned_entries: Vec<ArkheHash>,
    pub retention_reason: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ErasureStatus { Pending, InProgress, Completed, Rejected, Expired }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataPortabilityRequest {
    pub subject: ArkheDid,
    pub request_id: String,
    pub format: ExportFormat,
    pub status: PortabilityStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExportFormat { Json, JsonLd, Csv }

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PortabilityStatus { Pending, Processing, Ready, Failed, Expired }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataResidencyPolicy {
    pub data_category: String,
    pub allowed_jurisdictions: Vec<String>,
    pub requires_consent: bool,
    pub retention_days: u32,
}

pub struct GdprEngine {
    policies: HashMap<String, DataResidencyPolicy>,
}

impl GdprEngine {
    pub fn new() -> Self { Self { policies: HashMap::new() } }
    pub fn add_policy(&mut self, p: DataResidencyPolicy) { self.policies.insert(p.data_category.clone(), p); }
    pub fn check_jurisdiction(&self, category: &str, jurisdiction: &str) -> Result<(), String> {
        self.policies.get(category)
            .ok_or_else(|| format!("No policy for '{}'", category))
            .and_then(|p| {
                if p.allowed_jurisdictions.iter().any(|j| j == jurisdiction) {
                    Ok(())
                } else {
                    Err(format!("Jurisdiction '{}' not allowed for '{}'", jurisdiction, category))
                }
            })
    }
}

impl Default for GdprEngine { fn default() -> Self { Self::new() } }
