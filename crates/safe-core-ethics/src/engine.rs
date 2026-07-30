use crate::{EthicsRule, EthicsEngine, EthicsVerdict, EthicsError, rule::Severity};
use async_trait::async_trait;

pub struct Lean4Verifier {
    rules: Vec<EthicsRule>,
}

impl Lean4Verifier {
    pub fn new(_db: Option<String>) -> Self {
        Self { rules: Vec::new() }
    }
}

#[async_trait]
impl EthicsEngine for Lean4Verifier {
    async fn evaluate(&self, action: &str, context: &serde_json::Value) -> Result<EthicsVerdict, EthicsError> {
        for rule in &self.rules {
            if rule.action == action {
                if !rule.enabled {
                    continue;
                }

                let valid = if rule.constraint == "context.percentage <= 20" {
                    context.get("percentage")
                        .and_then(|v| v.as_f64())
                        .map(|p| p <= 20.0)
                        .unwrap_or(false)
                } else if rule.constraint == "context.amount <= 100000" {
                    context.get("amount")
                        .and_then(|v| v.as_f64())
                        .map(|a| a <= 100000.0)
                        .unwrap_or(false)
                } else {
                    true
                };

                if !valid {
                    let verdict = match rule.severity {
                        Severity::Block => "Block",
                        Severity::RequireApproval => "RequireApproval",
                        Severity::Allow => "Allow",
                    };
                    return Ok(EthicsVerdict {
                        verdict: verdict.to_string(),
                        reason: format!("Bloqueado por '{}'", rule.id),
                        rule_id: Some(rule.id.clone()),
                    });
                }
            }
        }

        Ok(EthicsVerdict {
            verdict: "Allow".to_string(),
            reason: "Permitido".to_string(),
            rule_id: None,
        })
    }

    async fn load_rules(&mut self, rules: Vec<EthicsRule>) -> Result<(), EthicsError> {
        self.rules = rules;
        Ok(())
    }

    async fn list_rules(&self) -> Vec<EthicsRule> {
        self.rules.clone()
    }
}
