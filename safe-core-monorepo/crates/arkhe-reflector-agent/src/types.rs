use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectionReport {
    pub session_id: String,
    pub timestamp: DateTime<Utc>,
    pub causal_patterns: Vec<ExtractedPattern>,
    pub procedural_skills: Vec<ExtractedPattern>,
    pub self_corrections: Vec<String>,
    pub recommendations: Vec<String>,
    pub quality_score: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedPattern {
    pub id: String,
    pub pattern_type: PatternType,
    pub description: String,
    pub trigger: String,
    pub confidence: f32,
    pub source_turns: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PatternType { CausalRule, ProceduralSkill, NegativeConstraint, SelfCorrection }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReflectorConfig {
    pub min_confidence: f32,
    pub max_patterns_per_session: usize,
}

impl Default for ReflectorConfig {
    fn default() -> Self {
        Self { min_confidence: 0.5, max_patterns_per_session: 20 }
    }
}
