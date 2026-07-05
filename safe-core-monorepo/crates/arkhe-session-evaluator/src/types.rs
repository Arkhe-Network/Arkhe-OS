use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionTrajectory {
    pub id: String,
    pub agent_did: String,
    pub turns: Vec<Turn>,
    pub artifacts: Vec<Artifact>,
    pub start_time: DateTime<Utc>,
    pub end_time: Option<DateTime<Utc>>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Turn {
    pub id: String,
    pub role: TurnRole,
    pub content: String,
    pub timestamp: DateTime<Utc>,
    pub reasoning: Option<String>,
    pub validation: Option<String>,
    pub artifacts: Vec<String>,
    pub confidence: Option<f32>,
    pub causal_links: Vec<CausalLink>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TurnRole { User, Assistant, System, Tool }

impl std::fmt::Display for TurnRole {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::User => write!(f, "user"),
            Self::Assistant => write!(f, "assistant"),
            Self::System => write!(f, "system"),
            Self::Tool => write!(f, "tool"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CausalLink {
    pub from_turn: String,
    pub to_turn: String,
    pub relation: CausalRelation,
    pub strength: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum CausalRelation { Premise, Correction, Refinement, Validation }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Artifact {
    pub id: String,
    pub artifact_type: ArtifactType,
    pub content: String,
    pub metadata: HashMap<String, serde_json::Value>,
    pub compilable: Option<bool>,
    pub tests_passed: Option<bool>,
    pub errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ArtifactType { Code, Test, Configuration, Architecture, Documentation, Other }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DimensionScore {
    pub score: f32,
    pub details: String,
    pub evidence: Vec<String>,
}

impl DimensionScore {
    pub fn new(score: f32, details: impl Into<String>) -> Self {
        Self { score: score.clamp(0.0, 1.0), details: details.into(), evidence: Vec::new() }
    }
    pub fn with_evidence(mut self, evidence: Vec<String>) -> Self { self.evidence = evidence; self }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub session_id: String,
    pub overall_score: f32,
    pub dimensions: Vec<EvaluationDimension>,
    pub summary: String,
    pub highlights: Vec<String>,
    pub concerns: Vec<String>,
    pub suggestions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationDimension {
    pub name: String,
    pub score: f32,
    pub weight: f32,
    pub details: String,
    pub evidence: Vec<String>,
}
