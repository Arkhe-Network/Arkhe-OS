//! Cathedral ARKHE v28.2 — Agent Loop
//! ReAct-style agent with Cathedral memory, planning, and guardrails.
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-AGENT-LOOP-2026-06-15
//! Arquiteto ORCID: 0009-0005-2697-4668

use std::collections::VecDeque;
use std::sync::Arc;
use tokio::sync::Mutex;
use serde::{Deserialize, Serialize};

/// Maximum agent steps before forced termination.
const MAX_AGENT_STEPS: u32 = 50;
/// Maximum tool calls per step.
const MAX_TOOL_CALLS_PER_STEP: u32 = 5;

/// Cathedral Agent — autonomous executor with ReAct loop.
pub struct CathedralAgent {
    pub config: AgentConfig,
    pub memory: Arc<Mutex<AgentMemory>>,
    pub tool_registry: ToolRegistry,
    pub planner: Box<dyn Planner>,
    pub guardrails: Guardrails,
    pub llm_client: Arc<dyn LlmClient>,
    pub telemetry: cathedral_embodied_no_std::telemetry::TelemetryCollector,
    pub step_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    pub name: String,
    pub system_prompt: String,
    pub model_id: String,
    pub temperature: f32,
    pub max_tokens: u32,
    pub tools: Vec<String>, // enabled tool names
    pub planning_strategy: PlanningStrategy,
    pub memory_config: MemoryConfig,
    pub guardrail_config: GuardrailConfig,
    pub cathedral_policy_hash: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum PlanningStrategy {
    ReAct,           // Reasoning + Acting
    ChainOfThought,  // Step-by-step reasoning
    TreeOfThoughts,  // Branching reasoning
    PlanAndExecute,  // Generate plan first, then execute
    Reflexion,       // Self-reflection after errors
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryConfig {
    pub short_term_capacity: usize,
    pub long_term_enabled: bool,
    pub vector_db_url: Option<String>,
    pub embedding_model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardrailConfig {
    pub content_filter_enabled: bool,
    pub max_tool_execution_time_secs: u64,
    pub forbidden_tools: Vec<String>,
    pub required_memory_proof_for: Vec<String>, // tool names
    pub output_moderation_threshold: f32, // 0.0-1.0
}

/// Agent memory — short-term (conversation) + long-term (RAG).
pub struct AgentMemory {
    short_term: VecDeque<MemoryEntry>,
    long_term: Option<Box<dyn VectorStore>>,
    config: MemoryConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub timestamp: u64,
    pub role: String, // "observation", "thought", "action", "result"
    pub content: String,
    pub embedding: Option<Vec<f32>>,
    pub importance: f32, // 0.0-1.0, for memory consolidation
}

#[async_trait::async_trait]
pub trait VectorStore: Send + Sync {
    async fn add(&mut self, entry: &MemoryEntry) -> Result<(), String>;
    async fn search(&self, query: &str, k: usize) -> Result<Vec<MemoryEntry>, String>;
    async fn clear(&mut self) -> Result<(), String>;
}

/// Tool registry — all available tools.
pub struct ToolRegistry {
    pub tools: std::collections::HashMap<String, Box<dyn Tool>>,
}

impl ToolRegistry {
    pub fn new() -> Self {
        Self {
            tools: std::collections::HashMap::new(),
        }
    }

    pub fn register(&mut self, tool: Box<dyn Tool>) {
        self.tools.insert(tool.name().to_string(), tool);
    }

    pub fn get(&self, name: &str) -> Option<&Box<dyn Tool>> {
        self.tools.get(name)
    }
}

#[async_trait::async_trait]
pub trait Tool: Send + Sync {
    fn name(&self) -> &str;
    fn description(&self) -> &str;
    fn parameters_schema(&self) -> serde_json::Value;
    async fn execute(&self, params: serde_json::Value) -> Result<ToolResult, ToolError>;
    fn requires_memory_proof(&self) -> bool;
    fn risk_level(&self) -> RiskLevel;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub success: bool,
    pub output: String,
    pub metadata: serde_json::Value,
    pub error: Option<String>,
}

#[derive(Debug, Clone)]
pub enum ToolError {
    InvalidParameters(String),
    ExecutionFailed(String),
    Timeout,
    Forbidden,
    MemoryProofRequired,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RiskLevel {
    Low, Medium, High, Critical,
}

/// Planner interface.
#[async_trait::async_trait]
pub trait Planner: Send + Sync {
    async fn plan(&self, goal: &str, memory: &AgentMemory, tools: &[&dyn Tool]) -> Result<Plan, PlanError>;
    async fn reflect(&self, memory: &AgentMemory) -> Result<String, PlanError>;
}

#[derive(Debug, Clone)]
pub struct Plan {
    pub steps: Vec<PlanStep>,
    pub estimated_cost: f64,
    pub confidence: f32,
}

#[derive(Debug, Clone)]
pub struct PlanStep {
    pub action: String,
    pub tool: Option<String>,
    pub reasoning: String,
    pub expected_outcome: String,
}

#[derive(Debug, Clone)]
pub enum PlanError {
    NoPlanFound,
    InvalidGoal(String),
    ToolsUnavailable,
}

/// Guardrails — safety and policy enforcement.
pub struct Guardrails {
    pub config: GuardrailConfig,
    pub content_filter: Option<Box<dyn ContentFilter>>,
}

#[async_trait::async_trait]
pub trait ContentFilter: Send + Sync {
    async fn check_input(&self, text: &str) -> Result<FilterResult, String>;
    async fn check_output(&self, text: &str) -> Result<FilterResult, String>;
}

#[derive(Debug, Clone)]
pub struct FilterResult {
    pub allowed: bool,
    pub flagged: bool,
    pub categories: Vec<String>,
    pub score: f32,
}

/// LLM client abstraction.
#[async_trait::async_trait]
pub trait LlmClient: Send + Sync {
    async fn chat(&self, messages: Vec<Message>, tools: Option<Vec<ToolDefinition>>) -> Result<LlmResponse, String>;
    async fn embed(&self, text: &str) -> Result<Vec<f32>, String>;
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String, // "system", "user", "assistant", "tool"
    pub content: String,
    pub tool_calls: Option<Vec<ToolCall>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value, // JSON Schema
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    pub function: ToolFunction,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolFunction {
    pub name: String,
    pub arguments: String, // JSON string
}

#[derive(Debug, Clone)]
pub struct LlmResponse {
    pub content: String,
    pub tool_calls: Vec<ToolCall>,
    pub usage: Usage,
    pub finish_reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Usage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

// ============================================================
// Agent Implementation
// ============================================================

impl CathedralAgent {
    pub fn new(
        config: AgentConfig,
        tool_registry: ToolRegistry,
        planner: Box<dyn Planner>,
        guardrails: Guardrails,
        llm_client: Arc<dyn LlmClient>,
    ) -> Self {
        let memory = Arc::new(Mutex::new(AgentMemory {
            short_term: VecDeque::with_capacity(config.memory_config.short_term_capacity),
            long_term: None, // initialized separately
            config: config.memory_config.clone(),
        }));

        Self {
            config,
            memory,
            tool_registry,
            planner,
            guardrails,
            llm_client,
            telemetry: cathedral_embodied_no_std::telemetry::TelemetryCollector::new("cathedral_agent"),
            step_count: 0,
        }
    }

    /// Main ReAct loop.
    pub async fn run(&mut self, goal: &str) -> Result<AgentResult, AgentError> {
        let start = std::time::Instant::now();
        self.step_count = 0;

        // Initial observation
        self.add_memory("observation", &format!("Goal: {}", goal), 1.0).await;

        loop {
            if self.step_count >= MAX_AGENT_STEPS {
                return Err(AgentError::MaxStepsExceeded);
            }
            self.step_count += 1;

            // 1. Retrieve relevant memory
            let relevant_memory = self.retrieve_memory(goal).await;

            // 2. Plan (if using PlanAndExecute or TreeOfThoughts)
            let plan = match self.config.planning_strategy {
                PlanningStrategy::PlanAndExecute | PlanningStrategy::TreeOfThoughts => {
                    let tools: Vec<&dyn Tool> = self.enabled_tools();
                    match self.planner.plan(goal, &relevant_memory, &tools).await {
                        Ok(p) => Some(p),
                        Err(_) => {
                            self.telemetry.record(
                                cathedral_embodied_no_std::telemetry::MetricKind::Custom("planning_failed"),
                                1.0,
                            );
                            None
                        }
                    }
                }
                _ => None,
            };

            // 3. LLM reasoning step
            let llm_response = self.reason(goal, &relevant_memory, plan.as_ref()).await?;

            // 4. Guardrails check on LLM output
            if let Some(filter) = &self.guardrails.content_filter {
                let check = filter.check_output(&llm_response.content).await
                    .map_err(|e| AgentError::GuardrailError(e))?;
                if !check.allowed {
                    self.add_memory("observation", "Output blocked by guardrails", 0.9).await;
                    continue;
                }
            }

            // 5. Execute tool calls
            if !llm_response.tool_calls.is_empty() {
                for tool_call in &llm_response.tool_calls {
                    if self.step_count >= MAX_AGENT_STEPS {
                        return Err(AgentError::MaxStepsExceeded);
                    }

                    let result = self.execute_tool(tool_call).await?;
                    self.add_memory("action", &format!("Tool {}: {:?}", tool_call.function.name, result), 0.8).await;

                    if result.success {
                        self.add_memory("observation", &result.output, 0.7).await;
                    } else {
                        self.add_memory("observation", &format!("Error: {:?}", result), 0.9).await;

                        // Reflexion on error
                        if matches!(self.config.planning_strategy, PlanningStrategy::Reflexion) {
                            let reflection = self.planner.reflect(&relevant_memory).await
                                .unwrap_or_else(|_| "Reflection failed".to_string());
                            self.add_memory("thought", &reflection, 0.9).await;
                        }
                    }
                }
            } else {
                // No tool calls — agent has final answer
                let elapsed = start.elapsed().as_secs_f64();
                self.telemetry.record(
                    cathedral_embodied_no_std::telemetry::MetricKind::TickTotalLatency,
                    elapsed * 1000.0,
                );

                return Ok(AgentResult {
                    final_answer: llm_response.content,
                    steps_taken: self.step_count,
                    tools_used: self.extract_tools_used(),
                    latency_secs: elapsed,
                    memory_consolidated: self.consolidate_memory().await,
                });
            }
        }
    }

    async fn reason(&self, goal: &str, memory: &AgentMemory, plan: Option<&Plan>) -> Result<LlmResponse, AgentError> {
        let mut messages = vec![
            Message {
                role: "system".to_string(),
                content: self.config.system_prompt.clone(),
                tool_calls: None,
            },
        ];

        // Add relevant memory as context
        for entry in &memory.short_term {
            messages.push(Message {
                role: entry.role.clone(),
                content: entry.content.clone(),
                tool_calls: None,
            });
        }

        // Add current goal
        messages.push(Message {
            role: "user".to_string(),
            content: goal.to_string(),
            tool_calls: None,
        });

        // Add plan if available
        if let Some(p) = plan {
            let plan_text = p.steps.iter()
                .map(|s| format!("- {}: {}", s.action, s.reasoning))
                .collect::<Vec<_>>()
                .join("\n");
            messages.push(Message {
                role: "system".to_string(),
                content: format!("Plan:\n{}", plan_text),
                tool_calls: None,
            });
        }

        let tools = self.enabled_tool_definitions();
        self.llm_client.chat(messages, Some(tools)).await
            .map_err(|e| AgentError::LlmError(e))
    }

    async fn execute_tool(&self, tool_call: &ToolCall) -> Result<ToolResult, AgentError> {
        let tool = self.tool_registry.tools.get(&tool_call.function.name)
            .ok_or(AgentError::ToolNotFound(tool_call.function.name.clone()))?;

        // Guardrails: check if tool is forbidden
        if self.guardrails.config.forbidden_tools.contains(&tool_call.function.name) {
            return Err(AgentError::ToolForbidden(tool_call.function.name.clone()));
        }

        // Guardrails: memory proof for high-risk tools
        if tool.requires_memory_proof() && !self.verify_memory_proof().await {
            return Err(AgentError::MemoryProofRequired(tool_call.function.name.clone()));
        }

        // Parse parameters
        let params: serde_json::Value = serde_json::from_str(&tool_call.function.arguments)
            .map_err(|e| AgentError::InvalidToolParameters(e.to_string()))?;

        // Execute with timeout
        let result = tokio::time::timeout(
            std::time::Duration::from_secs(self.guardrails.config.max_tool_execution_time_secs),
            tool.execute(params),
        ).await.map_err(|_| AgentError::ToolTimeout)?;

        result.map_err(|e| AgentError::ToolExecutionFailed(format!("{:?}", e)))
    }

    async fn add_memory(&self, role: &str, content: &str, importance: f32) {
        let mut memory = self.memory.lock().await;
        let entry = MemoryEntry {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            role: role.to_string(),
            content: content.to_string(),
            embedding: None, // computed asynchronously
            importance,
        };

        if memory.short_term.len() >= memory.config.short_term_capacity {
            // Consolidate oldest entry to long-term
            if let Some(old) = memory.short_term.pop_front() {
                if memory.config.long_term_enabled {
                    if let Some(lt) = &mut memory.long_term {
                        let _ = lt.add(&old).await;
                    }
                }
            }
        }

        memory.short_term.push_back(entry);
    }

    async fn retrieve_memory(&self, _query: &str) -> AgentMemory {
        let memory = self.memory.lock().await;
        // In production: embed query, search vector DB, return relevant entries
        AgentMemory {
            short_term: memory.short_term.clone(),
            long_term: None,
            config: memory.config.clone(),
        }
    }

    fn enabled_tools(&self) -> Vec<&dyn Tool> {
        self.tool_registry.tools.values()
            .filter(|t| self.config.tools.contains(&t.name().to_string()))
            .map(|t| t.as_ref())
            .collect()
    }

    fn enabled_tool_definitions(&self) -> Vec<ToolDefinition> {
        self.enabled_tools().iter()
            .map(|t| ToolDefinition {
                name: t.name().to_string(),
                description: t.description().to_string(),
                parameters: t.parameters_schema(),
            })
            .collect()
    }

    async fn verify_memory_proof(&self) -> bool {
        // In production: verify SPHINCS+ signature or ZK proof
        true // stub
    }

    fn extract_tools_used(&self) -> Vec<String> {
        // Extract from memory
        vec![] // stub
    }

    async fn consolidate_memory(&self) -> bool {
        // Compress and store to long-term memory
        true // stub
    }
}

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
    MaxStepsExceeded,
    LlmError(String),
    ToolNotFound(String),
    ToolForbidden(String),
    ToolTimeout,
    ToolExecutionFailed(String),
    InvalidToolParameters(String),
    MemoryProofRequired(String),
    GuardrailError(String),
    PlanningFailed(String),
}
