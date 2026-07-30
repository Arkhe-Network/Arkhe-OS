//! Cathedral ARKHE v28.2 — Guardrails
//! Content filtering, policy enforcement, and safety checks.
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-GUARDRAILS-2026-06-15
//! Arquiteto ORCID: 0009-0005-2697-4668

use serde::{Deserialize, Serialize};
use regex::Regex;

/// Multi-layer guardrail system.
pub struct CathedralGuardrails {
    pub config: GuardrailConfig,
    pub content_filter: Box<dyn ContentFilter>,
    pub policy_validator: Box<dyn PolicyValidator>,
    pub rate_limiter: RateLimiter,
}

impl CathedralGuardrails {
    pub fn new(
        config: GuardrailConfig,
        content_filter: Box<dyn ContentFilter>,
        policy_validator: Box<dyn PolicyValidator>,
        rate_limiter: RateLimiter,
    ) -> Self {
        Self {
            config,
            content_filter,
            policy_validator,
            rate_limiter,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardrailConfig {
    pub content_filter_enabled: bool,
    pub max_tokens_per_minute: u32,
    pub max_tools_per_step: u32,
    pub forbidden_patterns: Vec<String>,
    pub required_disclaimers: Vec<String>,
    pub output_moderation_threshold: f32,
    pub cathedral_policy_version: String,
}

impl Default for GuardrailConfig {
    fn default() -> Self {
        Self {
            content_filter_enabled: true,
            max_tokens_per_minute: 1000,
            max_tools_per_step: 5,
            forbidden_patterns: vec![],
            required_disclaimers: vec![],
            output_moderation_threshold: 0.7,
            cathedral_policy_version: "v28.2".to_string(),
        }
    }
}

#[async_trait::async_trait]
pub trait ContentFilter: Send + Sync {
    async fn check_input(&self, text: &str) -> Result<FilterResult, String>;
    async fn check_output(&self, text: &str) -> Result<FilterResult, String>;
    async fn check(&self, text: &str) -> FilterResult;
    async fn classify(&self, text: &str) -> Vec<ContentCategory>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FilterResult {
    pub allowed: bool,
    pub score: f32, // 0.0 = safe, 1.0 = blocked
    pub categories: Vec<ContentCategory>,
    pub action: FilterAction,
    pub flagged: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FilterAction {
    Allow,
    Warn,
    Block,
    RequireHumanReview,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContentCategory {
    Hate, Violence, SelfHarm, Sexual, Harassment,
    Illegal, Malware, Deception, Privacy, None,
}

#[async_trait::async_trait]
pub trait PolicyValidator: Send + Sync {
    async fn validate_action(&self, action: &str, params: &serde_json::Value) -> PolicyResult;
    async fn check_compliance(&self, agent_output: &str) -> ComplianceResult;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyResult {
    pub compliant: bool,
    pub violations: Vec<PolicyViolation>,
    pub suggested_alternative: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyViolation {
    pub rule_id: String,
    pub severity: ViolationSeverity,
    pub description: String,
    pub remediation: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ViolationSeverity {
    Info, Warning, Critical, Emergency,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceResult {
    pub compliant: bool,
    pub score: f32,
    pub checks: Vec<ComplianceCheck>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComplianceCheck {
    pub name: String,
    pub passed: bool,
    pub details: String,
}

/// Token bucket rate limiter.
pub struct RateLimiter {
    tokens: std::sync::Mutex<f32>,
    max_tokens: f32,
    refill_rate: f32, // tokens per second
    last_refill: std::sync::Mutex<std::time::Instant>,
}

impl RateLimiter {
    pub fn new(max_tokens: f32, refill_rate: f32) -> Self {
        Self {
            tokens: std::sync::Mutex::new(max_tokens),
            max_tokens,
            refill_rate,
            last_refill: std::sync::Mutex::new(std::time::Instant::now()),
        }
    }

    pub fn acquire(&self, tokens: f32) -> bool {
        let mut current = self.tokens.lock().unwrap();
        let mut last = self.last_refill.lock().unwrap();

        let now = std::time::Instant::now();
        let elapsed = now.duration_since(*last).as_secs_f32();
        *current = (*current + elapsed * self.refill_rate).min(self.max_tokens);
        *last = now;

        if *current >= tokens {
            *current -= tokens;
            true
        } else {
            false
        }
    }
}

// ============================================================
// Implementations
// ============================================================

/// Regex-based content filter (fallback).
pub struct RegexContentFilter {
    forbidden_patterns: Vec<Regex>,
    moderation_threshold: f32,
}

impl RegexContentFilter {
    pub fn new(patterns: &[String], threshold: f32) -> Result<Self, regex::Error> {
        let regexes = patterns.iter()
            .map(|p| Regex::new(p))
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Self { forbidden_patterns: regexes, moderation_threshold: threshold })
    }
}

#[async_trait::async_trait]
impl ContentFilter for RegexContentFilter {
    async fn check_input(&self, text: &str) -> Result<FilterResult, String> {
        Ok(self.check(text).await)
    }

    async fn check_output(&self, text: &str) -> Result<FilterResult, String> {
        Ok(self.check(text).await)
    }

    async fn check(&self, text: &str) -> FilterResult {
        let mut score = 0.0f32;
        let mut categories = Vec::new();

        for pattern in &self.forbidden_patterns {
            if pattern.is_match(text) {
                score += 0.3;
                categories.push(ContentCategory::Hate); // simplified
            }
        }

        score = score.min(1.0);

        let action = if score >= self.moderation_threshold {
            FilterAction::Block
        } else if score >= self.moderation_threshold * 0.5 {
            FilterAction::Warn
        } else {
            FilterAction::Allow
        };

        FilterResult {
            allowed: action != FilterAction::Block,
            score,
            categories,
            action,
            flagged: action != FilterAction::Allow,
        }
    }

    async fn classify(&self, _text: &str) -> Vec<ContentCategory> {
        vec![ContentCategory::None] // stub
    }
}

/// Cathedral policy validator.
pub struct CathedralPolicyValidator {
    policy_hash: String,
}

impl CathedralPolicyValidator {
    pub fn new(policy_hash: String) -> Self {
        Self { policy_hash }
    }
}

#[async_trait::async_trait]
impl PolicyValidator for CathedralPolicyValidator {
    async fn validate_action(&self, action: &str, params: &serde_json::Value) -> PolicyResult {
        let mut violations = Vec::new();

        // Check for forbidden actions
        if action == "delete_all" {
            violations.push(PolicyViolation {
                rule_id: "POL-001".to_string(),
                severity: ViolationSeverity::Emergency,
                description: "Mass deletion requires explicit human approval".to_string(),
                remediation: "Request human-in-the-loop approval".to_string(),
            });
        }

        // Check for data exfiltration
        if action == "send_email" && params.get("external").and_then(|v| v.as_bool()).unwrap_or(false) {
            violations.push(PolicyViolation {
                rule_id: "POL-002".to_string(),
                severity: ViolationSeverity::Critical,
                description: "External communication requires audit trail".to_string(),
                remediation: "Enable memory proof logging".to_string(),
            });
        }

        PolicyResult {
            compliant: violations.is_empty(),
            violations,
            suggested_alternative: None,
        }
    }

    async fn check_compliance(&self, agent_output: &str) -> ComplianceResult {
        let checks = vec![
            ComplianceCheck {
                name: "cathedral_policy_version".to_string(),
                passed: agent_output.contains(&self.policy_hash),
                details: format!("Policy hash: {}", self.policy_hash),
            },
            ComplianceCheck {
                name: "no_pii_leak".to_string(),
                passed: !agent_output.contains("SSN") && !agent_output.contains("password"),
                details: "PII scan complete".to_string(),
            },
            ComplianceCheck {
                name: "output_length".to_string(),
                passed: agent_output.len() < 10000,
                details: format!("Length: {}", agent_output.len()),
            },
        ];

        let score = checks.iter().filter(|c| c.passed).count() as f32 / checks.len() as f32;

        ComplianceResult {
            compliant: score >= 0.9,
            score,
            checks,
        }
    }
}
