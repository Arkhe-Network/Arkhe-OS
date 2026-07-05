// crates/arkhe-governance/src/audit_policy.rs
use arkhe_core::ArkheHash;
use arkhe_identity::ArkheDid;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AccountabilityRecord {
    pub action: String,
    pub subject: ArkheDid,
    pub timestamp: DateTime<Utc>,
    pub previous_hash: Option<ArkheHash>,
    pub current_hash: ArkheHash,
}

pub struct AuditChain {
    records: Vec<AccountabilityRecord>,
}

impl AuditChain {
    pub fn new() -> Self { Self { records: Vec::new() } }
    pub fn add(&mut self, record: AccountabilityRecord) { self.records.push(record); }
    pub fn verify(&self) -> bool {
        self.records.windows(2).all(|w| w[1].previous_hash == Some(w[0].current_hash))
    }
}

impl Default for AuditChain { fn default() -> Self { Self::new() } }
