// crates/arkhe-mobile-bridge/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

use arkhe_audit_trail::{AuditCategory, AuditOutcome, AuditTrail, NewAuditEntry};
use arkhe_configuration::Configuration;
use arkhe_policy_as_code::{Condition, Policy, PolicyContext, PolicyEvaluator, PolicyRule, Verdict};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum MobileBridgeError {
    #[error("policy error: {0}")]
    Policy(String),
    #[error("audit error: {0}")]
    Audit(String),
}

pub type MobileResult<T> = Result<T, MobileBridgeError>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MobilePolicyResult {
    pub allowed: bool,
    pub reason: String,
    pub audit_id: String,
}

pub struct MobileBridge {
    evaluator: Mutex<PolicyEvaluator>,
    audit_trail: Mutex<AuditTrail>,
    config: Configuration,
}

impl MobileBridge {
    pub fn new() -> MobileResult<Self> {
        let mut evaluator = PolicyEvaluator::new();
        evaluator.add_policy(Policy {
            id: "mobile_default".into(),
            name: "Mobile Default".into(),
            description: "Default policy for mobile clients".into(),
            rules: vec![
                PolicyRule {
                    id: "allow_read".into(),
                    condition: Condition::Equals { field: "action".into(), value: serde_json::json!("read") },
                    verdict: Verdict::Allow,
                    priority: 0,
                    reason: "Read operations allowed on mobile".into(),
                },
            ],
            default_verdict: Verdict::Deny,
            active: true,
            tags: vec!["mobile".into()],
        });
        Ok(Self { evaluator: Mutex::new(evaluator), audit_trail: Mutex::new(AuditTrail::new()), config: Configuration::new() })
    }

    pub fn check_policy(&self, actor_did: &str, action: &str, resource: &str) -> MobileResult<MobilePolicyResult> {
        let ctx = PolicyContext {
            actor_did: actor_did.into(),
            action: action.into(),
            resource: resource.into(),
            attributes: HashMap::new(),
            timestamp: chrono::Utc::now(),
        };
        let verdict = self.evaluator.lock().unwrap().evaluate_all(&ctx)
            .map_err(|e| MobileBridgeError::Policy(e.to_string()))?;
        let allowed = verdict.verdict == Verdict::Allow;
        let audit_id = uuid::Uuid::new_v4().to_string();
        let mut details = HashMap::new();
        details.insert("allowed".into(), serde_json::json!(allowed));
        details.insert("action".into(), serde_json::json!(action));
        details.insert("resource".into(), serde_json::json!(resource));
        self.audit_trail.lock().unwrap().record(NewAuditEntry {
            category: AuditCategory::PolicyDecision,
            action: format!("mobile:{}", action),
            actor_did: actor_did.into(),
            resource: resource.into(),
            outcome: if allowed { AuditOutcome::Success } else { AuditOutcome::Denied },
            details,
        }).map_err(|e| MobileBridgeError::Audit(e.to_string()))?;
        Ok(MobilePolicyResult { allowed, reason: verdict.reason, audit_id })
    }

    pub fn get_audit_log(&self) -> MobileResult<String> {
        let trail = self.audit_trail.lock().unwrap();
        serde_json::to_string(&trail.entries()).map_err(|e| MobileBridgeError::Audit(e.to_string()))
    }

    pub fn verify_audit(&self) -> MobileResult<bool> {
        let trail = self.audit_trail.lock().unwrap();
        trail.verify_integrity().map_err(|e| MobileBridgeError::Audit(e.to_string()))?;
        Ok(true)
    }
}

impl Default for MobileBridge { fn default() -> Self { Self::new().unwrap() } }
