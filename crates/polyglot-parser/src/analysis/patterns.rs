use crate::ast::Node;
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VulnerabilityPattern {
    pub id: String,
    pub title: String,
    pub description: String,
    pub cwe_id: Option<String>,
    pub languages: Vec<String>,
    pub node_kind: String,
    pub node_matchers: Vec<NodeMatcher>,
    pub suggested_fix: Option<String>,
    pub confidence: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeMatcher {
    pub field: String,
    pub operator: MatcherOperator,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MatcherOperator {
    Equals,
    Contains,
    StartsWith,
    EndsWith,
    Regex,
}

pub struct PatternMatcher {
    patterns: Vec<VulnerabilityPattern>,
}

impl PatternMatcher {
    pub fn new() -> Self {
        let mut matcher = Self { patterns: Vec::new() };
        matcher.load_default_patterns();
        matcher
    }

    fn load_default_patterns(&mut self) {
        self.patterns.push(VulnerabilityPattern {
            id: "PAT-001".to_string(),
            title: "Hardcoded Secret".to_string(),
            description: "Hardcoded API keys, passwords, or secrets detected in source code.".to_string(),
            cwe_id: Some("CWE-798".to_string()),
            languages: vec!["rust".to_string(), "python".to_string(), "go".to_string(), "typescript".to_string()],
            node_kind: "Literal".to_string(),
            node_matchers: vec![
                NodeMatcher {
                    field: "value".to_string(),
                    operator: MatcherOperator::Regex,
                    value: r#"(?i)(secret|api[_-]key|password|token|credential)"#.to_string(),
                }
            ],
            suggested_fix: Some("Store secrets in environment variables or secure vaults.".to_string()),
            confidence: 0.85,
        });
    }

    pub fn match_node(&self, node: &Node) -> Vec<&VulnerabilityPattern> {
        let node_lang = format!("{:?}", node.language).to_lowercase();
        let node_kind_str = format!("{:?}", node.kind).to_lowercase();
        let mut matched = Vec::new();
        for pattern in &self.patterns {
            if !pattern.languages.is_empty() && !pattern.languages.iter().any(|l| l.to_lowercase() == node_lang) {
                continue;
            }
            if !pattern.node_kind.is_empty() && pattern.node_kind.to_lowercase() != node_kind_str && pattern.node_kind != "*" {
                continue;
            }
            let mut all_match = true;
            for matcher in &pattern.node_matchers {
                let value = node.metadata.get(&matcher.field).and_then(|v| {
                    if let crate::ast::MetadataValue::String(s) = v {
                        Some(s)
                    } else {
                        None
                    }
                });
                let matches = match (value, &matcher.operator) {
                    (Some(v), MatcherOperator::Equals) => v == &matcher.value,
                    (Some(v), MatcherOperator::Contains) => v.contains(&matcher.value),
                    (Some(v), MatcherOperator::StartsWith) => v.starts_with(&matcher.value),
                    (Some(v), MatcherOperator::EndsWith) => v.ends_with(&matcher.value),
                    (Some(v), MatcherOperator::Regex) => {
                        if let Ok(re) = Regex::new(&matcher.value) {
                            re.is_match(v)
                        } else { false }
                    }
                    _ => false,
                };
                if !matches { all_match = false; break; }
            }
            if all_match { matched.push(pattern); }
        }
        matched
    }
}
