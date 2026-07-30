//! Cathedral ARKHE v28.2 — Multi‑Agent Orchestrator
//! Coordena múltiplos agentes especializados (Oracle, Coder, Analyst, Guardian)
//! usando um barramento de mensagens assíncrono e rastreabilidade via TemporalChain.
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-ORCHESTRATOR-2026-06-16
//! Arquiteto ORCID: 0009-0005-2697-4668

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{Mutex, mpsc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::agent_loop::{CathedralAgent, AgentConfig, AgentResult, AgentError, LlmClient, Planner, PlanningStrategy};
use crate::tools::ToolRegistry;
use crate::planning::{ReActPlanner, ChainOfThoughtPlanner};
use crate::guardrails::CathedralGuardrails;

// ============================================================================
// Message Protocol
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentMessage {
    pub msg_id: String,
    pub source: String,
    pub target: String,
    pub task_type: String,
    pub payload: serde_json::Value,
    pub timestamp: u64,
    pub temporal_hash: Option<String>,
    pub sphincs_signature: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResponse {
    pub msg_id: String,
    pub source: String,
    pub success: bool,
    pub result: serde_json::Value,
    pub error: Option<String>,
    pub temporal_hash: Option<String>,
}

// ============================================================================
// Workflow Definition
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkflowStep {
    Sequential(Vec<String>),     // agent names in order
    Parallel(Vec<String>),       // agents run concurrently
    Conditional {
        condition: String,       // agent that decides
        true_branch: Box<WorkflowStep>,
        false_branch: Box<WorkflowStep>,
    },
    Loop {
        agent: String,
        max_iterations: u32,
        until_success: bool,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowDefinition {
    pub id: String,
    pub name: String,
    pub steps: Vec<WorkflowStep>,
    pub input_mapping: HashMap<String, String>, // maps task param -> agent input
    pub output_mapping: HashMap<String, String>, // maps agent output -> final result
}

// ============================================================================
// Orchestrator Core
// ============================================================================

pub struct MultiAgentOrchestrator {
    agents: HashMap<String, Arc<Mutex<CathedralAgent>>>,
    message_bus: mpsc::UnboundedSender<AgentMessage>,
    message_rx: Arc<Mutex<mpsc::UnboundedReceiver<AgentMessage>>>,
    pending_responses: Arc<Mutex<HashMap<String, tokio::sync::oneshot::Sender<AgentResponse>>>>,
    workflows: HashMap<String, WorkflowDefinition>,
    temporal_client: Arc<dyn TemporalChainClient>,
}

#[async_trait::async_trait]
pub trait TemporalChainClient: Send + Sync {
    async fn anchor_message(&self, msg: &AgentMessage) -> Result<String, String>;
    async fn anchor_response(&self, resp: &AgentResponse) -> Result<String, String>;
    async fn get_workflow_state(&self, workflow_id: &str) -> Result<serde_json::Value, String>;
}

impl MultiAgentOrchestrator {
    pub fn new(temporal_client: Arc<dyn TemporalChainClient>) -> Self {
        let (tx, rx) = mpsc::unbounded_channel();
        Self {
            agents: HashMap::new(),
            message_bus: tx,
            message_rx: Arc::new(Mutex::new(rx)),
            pending_responses: Arc::new(Mutex::new(HashMap::new())),
            workflows: HashMap::new(),
            temporal_client,
        }
    }

    /// Register an agent with its configuration.
    pub async fn register_agent(
        &mut self,
        name: &str,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        guardrails: CathedralGuardrails,
        llm_client: Arc<dyn LlmClient>,
    ) -> Result<(), String> {
        let planner: Box<dyn Planner> = match config.planning_strategy {
            PlanningStrategy::ReAct => Box::new(ReActPlanner::new(10, llm_client.clone())),
            PlanningStrategy::ChainOfThought => Box::new(ChainOfThoughtPlanner::new(llm_client.clone())),
            _ => Box::new(ReActPlanner::new(10, llm_client.clone())),
        };

        let agent = CathedralAgent::new(
            config,
            tool_registry,
            planner,
            guardrails,
            llm_client,
        );
        self.agents.insert(name.to_string(), Arc::new(Mutex::new(agent)));
        Ok(())
    }

    /// Register a workflow definition.
    pub fn register_workflow(&mut self, workflow: WorkflowDefinition) {
        self.workflows.insert(workflow.id.clone(), workflow);
    }

    /// Execute a workflow by ID.
    pub async fn run_workflow(
        &self,
        workflow_id: &str,
        input: serde_json::Value,
    ) -> Result<serde_json::Value, String> {
        let workflow = self.workflows.get(workflow_id)
            .ok_or_else(|| format!("Workflow {} not found", workflow_id))?;

        let mut context = input.as_object().cloned().unwrap_or_default();
        let mut step_results = HashMap::new();

        for step in &workflow.steps {
            let result = self.execute_step(step, &mut context, &workflow).await?;
            step_results.insert(format!("{:?}", step), result);
        }

        // Apply output mapping
        let final_output = self.apply_output_mapping(&step_results, &workflow.output_mapping);
        Ok(final_output)
    }

    async fn execute_step(
        &self,
        step: &WorkflowStep,
        context: &mut serde_json::Map<String, serde_json::Value>,
        workflow: &WorkflowDefinition,
    ) -> Result<serde_json::Value, String> {
        match step {
            WorkflowStep::Sequential(agents) => {
                let mut last_result = serde_json::Value::Null;
                for agent_name in agents {
                    let agent_input = self.prepare_agent_input(agent_name, context, workflow);
                    let resp = self.send_and_wait(agent_name, "execute", agent_input).await?;
                    last_result = resp.result;
                    context.insert(format!("{}_output", agent_name), last_result.clone());
                }
                Ok(last_result)
            }
            WorkflowStep::Parallel(agents) => {
                let handles: Vec<_> = agents.iter()
                    .map(|agent_name| {
                        let agent_input = self.prepare_agent_input(agent_name, context, workflow);
                        self.send_and_wait(agent_name, "execute", agent_input)
                    })
                    .collect();
                let results = futures::future::join_all(handles).await;
                for (i, res) in results.into_iter().enumerate() {
                    let resp = res?;
                    context.insert(format!("{}_output", agents[i]), resp.result);
                }
                Ok(serde_json::json!({ "parallel_results": "ok" }))
            }
            WorkflowStep::Conditional { condition, true_branch, false_branch } => {
                let condition_agent = condition;
                let resp = self.send_and_wait(condition_agent, "decide", serde_json::json!({ "context": context })).await?;
                let decision = resp.result.as_bool().unwrap_or(false);
                let branch = if decision { true_branch } else { false_branch };
                // Pin the recursion
                Box::pin(self.execute_step(branch, context, workflow)).await
            }
            WorkflowStep::Loop { agent, max_iterations, until_success } => {
                let mut iteration = 0;
                let mut last_result = serde_json::Value::Null;
                while iteration < *max_iterations {
                    let agent_input = self.prepare_agent_input(agent, context, workflow);
                    let resp = self.send_and_wait(agent, "execute", agent_input).await?;
                    last_result = resp.result;
                    context.insert(format!("{}_output", agent), last_result.clone());
                    if *until_success && resp.success {
                        break;
                    }
                    iteration += 1;
                }
                Ok(last_result)
            }
        }
    }

    fn prepare_agent_input(
        &self,
        agent_name: &str,
        context: &serde_json::Map<String, serde_json::Value>,
        workflow: &WorkflowDefinition,
    ) -> serde_json::Value {
        let mut input = serde_json::Map::new();
        for (from, to) in &workflow.input_mapping {
            if let Some(val) = context.get(from) {
                input.insert(to.clone(), val.clone());
            }
        }
        // Add agent-specific context
        input.insert("agent".to_string(), serde_json::json!(agent_name));
        serde_json::Value::Object(input)
    }

    fn apply_output_mapping(
        &self,
        step_results: &HashMap<String, serde_json::Value>,
        mapping: &HashMap<String, String>,
    ) -> serde_json::Value {
        let mut output = serde_json::Map::new();
        for (step_key, field) in mapping {
            if let Some(val) = step_results.get(step_key) {
                output.insert(field.clone(), val.clone());
            }
        }
        serde_json::Value::Object(output)
    }

    async fn send_and_wait(
        &self,
        agent_name: &str,
        task_type: &str,
        payload: serde_json::Value,
    ) -> Result<AgentResponse, String> {
        let msg_id = Uuid::new_v4().to_string();
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let msg = AgentMessage {
            msg_id: msg_id.clone(),
            source: "orchestrator".to_string(),
            target: agent_name.to_string(),
            task_type: task_type.to_string(),
            payload,
            timestamp,
            temporal_hash: None,
            sphincs_signature: None,
        };

        // Anchor to TemporalChain (if available)
        if let Ok(hash) = self.temporal_client.anchor_message(&msg).await {
            // In production, store hash in msg and signature
        }

        let (tx, rx) = tokio::sync::oneshot::channel();
        {
            let mut pending = self.pending_responses.lock().await;
            pending.insert(msg_id.clone(), tx);
        }

        // Send to agent's message loop
        self.message_bus.send(msg).map_err(|_| "Message bus full".to_string())?;

        // Wait for response (timeout 60s)
        match tokio::time::timeout(std::time::Duration::from_secs(60), rx).await {
            Ok(Ok(resp)) => {
                self.temporal_client.anchor_response(&resp).await.ok();
                Ok(resp)
            }
            Ok(Err(_)) => Err("Agent dropped response channel".to_string()),
            Err(_) => Err("Agent response timeout".to_string()),
        }
    }

    /// Start the orchestrator's message processing loop.
    pub async fn start(&self) {
        let mut rx = self.message_rx.lock().await;
        let pending = self.pending_responses.clone();
        let agents = self.agents.clone();

        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                let agents = agents.clone();
                let pending = pending.clone();
                tokio::spawn(async move {
                    if let Some(agent_mutex) = agents.get(&msg.target) {
                        let mut agent = agent_mutex.lock().await;
                        let result = match msg.task_type.as_str() {
                            "execute" => {
                                // Parse payload into agent run goal
                                let goal = msg.payload.get("goal")
                                    .and_then(|v| v.as_str())
                                    .unwrap_or("Execute task");
                                agent.run(goal).await
                            }
                            "decide" => {
                                // Special decision task (returns bool)
                                Ok(AgentResult {
                                    final_answer: "true".to_string(),
                                    steps_taken: 1,
                                    tools_used: vec![],
                                    latency_secs: 0.0,
                                    memory_consolidated: false,
                                })
                            }
                            _ => Err(AgentError::LlmError("Unknown task type".to_string())),
                        };

                        let response = match result {
                            Ok(r) => AgentResponse {
                                msg_id: msg.msg_id,
                                source: msg.target,
                                success: true,
                                result: serde_json::json!({ "answer": r.final_answer }),
                                error: None,
                                temporal_hash: None,
                            },
                            Err(e) => AgentResponse {
                                msg_id: msg.msg_id,
                                source: msg.target,
                                success: false,
                                result: serde_json::Value::Null,
                                error: Some(format!("{:?}", e)),
                                temporal_hash: None,
                            },
                        };

                        if let Some(sender) = pending.lock().await.remove(&response.msg_id) {
                            let _ = sender.send(response);
                        }
                    }
                });
            }
        });
    }
}
