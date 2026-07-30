use async_trait::async_trait;
use serde::{Deserialize, Serialize};

pub type AgentId = String;

#[derive(Debug, Clone)]
pub struct AgentResult {
    pub final_answer: String,
    pub steps_taken: u32,
    pub tools_used: Vec<String>,
    pub latency_secs: f64,
    pub memory_consolidated: bool,
}

#[derive(Debug, Clone)]
pub enum AgentError {
    ToolError(String),
}

#[async_trait]
pub trait CathedralAgent: Send + Sync {
    async fn run(&mut self, goal: &str) -> Result<AgentResult, AgentError>;
    fn id(&self) -> AgentId;
}
