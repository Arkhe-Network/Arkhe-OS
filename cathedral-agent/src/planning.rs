//! Cathedral ARKHE v28.2 — Planning Strategies
//! ReAct, Chain-of-Thought, Tree-of-Thoughts, Plan-and-Execute, Reflexion.
//!
//! Selo: CATHEDRAL-ARKHE-v28.2-PLANNING-2026-06-15
//! Arquiteto ORCID: 0009-0005-2697-4668

use super::agent_loop::{Planner, Plan, PlanStep, PlanError, AgentMemory, Tool};

/// ReAct planner — interleaves reasoning and acting.
pub struct ReActPlanner {
    max_iterations: u32,
    llm_client: Arc<dyn super::agent_loop::LlmClient>,
}

impl ReActPlanner {
    pub fn new(max_iterations: u32, llm_client: Arc<dyn super::agent_loop::LlmClient>) -> Self {
        Self { max_iterations, llm_client }
    }
}

#[async_trait::async_trait]
impl Planner for ReActPlanner {
    async fn plan(&self, goal: &str, _memory: &AgentMemory, _tools: &[&dyn Tool]) -> Result<Plan, PlanError> {
        // ReAct doesn't pre-plan; it reasons at each step
        // Return a single-step plan that triggers reasoning
        Ok(Plan {
            steps: vec![PlanStep {
                action: "reason_and_act".to_string(),
                tool: None,
                reasoning: format!("ReAct loop for goal: {}", goal),
                expected_outcome: "Progress toward goal".to_string(),
            }],
            estimated_cost: 0.1,
            confidence: 0.8,
        })
    }

    async fn reflect(&self, memory: &AgentMemory) -> Result<String, PlanError> {
        let reflection_prompt = format!(
            "Review the following memory and identify what went wrong and how to improve:\n{}",
            format_memory(memory)
        );

        let messages = vec![super::agent_loop::Message {
            role: "system".to_string(),
            content: "You are a self-reflective agent. Analyze errors and suggest improvements.".to_string(),
            tool_calls: None,
        }, super::agent_loop::Message {
            role: "user".to_string(),
            content: reflection_prompt,
            tool_calls: None,
        }];

        match self.llm_client.chat(messages, None).await {
            Ok(response) => Ok(response.content),
            Err(_) => Err(PlanError::NoPlanFound),
        }
    }
}

/// Chain-of-Thought planner — generates step-by-step reasoning before acting.
pub struct ChainOfThoughtPlanner {
    llm_client: Arc<dyn super::agent_loop::LlmClient>,
}

impl ChainOfThoughtPlanner {
    pub fn new(llm_client: Arc<dyn super::agent_loop::LlmClient>) -> Self {
        Self { llm_client }
    }
}

#[async_trait::async_trait]
impl Planner for ChainOfThoughtPlanner {
    async fn plan(&self, goal: &str, _memory: &AgentMemory, tools: &[&dyn Tool]) -> Result<Plan, PlanError> {
        let tool_descriptions: String = tools.iter()
            .map(|t| format!("- {}: {}", t.name(), t.description()))
            .collect::<Vec<_>>()
            .join("\n");

        let prompt = format!(
            "Goal: {}\n\nAvailable tools:\n{}\n\nThink step by step. \nGenerate a plan with specific tool calls.",
            goal, tool_descriptions
        );

        let messages = vec![super::agent_loop::Message {
            role: "user".to_string(),
            content: prompt,
            tool_calls: None,
        }];

        let response = self.llm_client.chat(messages, None).await
            .map_err(|_| PlanError::NoPlanFound)?;

        // Parse plan from LLM output
        let steps = parse_plan_from_text(&response.content, tools);

        Ok(Plan {
            steps,
            estimated_cost: 0.2,
            confidence: 0.75,
        })
    }

    async fn reflect(&self, _memory: &AgentMemory) -> Result<String, PlanError> {
        Ok("Chain-of-Thought does not use reflection.".to_string())
    }
}

/// Tree-of-Thoughts planner — explores multiple reasoning branches.
pub struct TreeOfThoughtsPlanner {
    llm_client: Arc<dyn super::agent_loop::LlmClient>,
    branching_factor: usize,
    _max_depth: usize,
}

impl TreeOfThoughtsPlanner {
    pub fn new(llm_client: Arc<dyn super::agent_loop::LlmClient>, branching_factor: usize, max_depth: usize) -> Self {
        Self { llm_client, branching_factor, _max_depth: max_depth }
    }
}

#[async_trait::async_trait]
impl Planner for TreeOfThoughtsPlanner {
    async fn plan(&self, goal: &str, _memory: &AgentMemory, tools: &[&dyn Tool]) -> Result<Plan, PlanError> {
        // Generate multiple candidate plans
        let mut candidates = Vec::new();

        for i in 0..self.branching_factor {
            let prompt = format!(
                "Goal: {}\nGenerate plan variant {} of {}. Be creative and diverse.",
                goal, i + 1, self.branching_factor
            );

            let messages = vec![super::agent_loop::Message {
                role: "user".to_string(),
                content: prompt,
                tool_calls: None,
            }];

            if let Ok(response) = self.llm_client.chat(messages, None).await {
                let steps = parse_plan_from_text(&response.content, tools);
                candidates.push(Plan {
                    steps,
                    estimated_cost: 0.15 * (i + 1) as f64,
                    confidence: 0.6 + (i as f32 * 0.05),
                });
            }
        }

        // Select best plan (highest confidence)
        candidates.into_iter()
            .max_by(|a, b| a.confidence.partial_cmp(&b.confidence).unwrap())
            .ok_or(PlanError::NoPlanFound)
    }

    async fn reflect(&self, _memory: &AgentMemory) -> Result<String, PlanError> {
        Ok("Tree-of-Thoughts uses branch evaluation, not reflection.".to_string())
    }
}

/// Plan-and-Execute planner — generates full plan upfront.
pub struct PlanAndExecutePlanner {
    llm_client: Arc<dyn super::agent_loop::LlmClient>,
}

#[async_trait::async_trait]
impl Planner for PlanAndExecutePlanner {
    async fn plan(&self, goal: &str, _memory: &AgentMemory, tools: &[&dyn Tool]) -> Result<Plan, PlanError> {
        let tool_descriptions = tools.iter()
            .map(|t| format!("- {}: {} (params: {:?})", t.name(), t.description(), t.parameters_schema()))
            .collect::<Vec<_>>()
            .join("\n");

        let prompt = format!(
            "Create a detailed execution plan for: {}\n\nAvailable tools:\n{}\n\nFormat each step as:\nSTEP N: [Action] - [Tool] - [Expected outcome]",
            goal, tool_descriptions
        );

        let messages = vec![super::agent_loop::Message {
            role: "system".to_string(),
            content: "You are a meticulous planner. Generate detailed, actionable plans.".to_string(),
            tool_calls: None,
        }, super::agent_loop::Message {
            role: "user".to_string(),
            content: prompt,
            tool_calls: None,
        }];

        let response = self.llm_client.chat(messages, None).await
            .map_err(|_| PlanError::NoPlanFound)?;

        let steps = parse_plan_from_text(&response.content, tools);

        Ok(Plan {
            steps,
            estimated_cost: 0.25,
            confidence: 0.85,
        })
    }

    async fn reflect(&self, _memory: &AgentMemory) -> Result<String, PlanError> {
        Ok("Plan-and-Execute reflects on plan failure, not per-step.".to_string())
    }
}

// ============================================================
// Helpers
// ============================================================

fn format_memory(memory: &AgentMemory) -> String {
    memory.short_term.iter()
        .map(|e| format!("[{}] {}: {}", e.timestamp, e.role, e.content))
        .collect::<Vec<_>>()
        .join("\n")
}

fn parse_plan_from_text(text: &str, tools: &[&dyn Tool]) -> Vec<PlanStep> {
    // Simplified parser — in production, use structured output or regex
    text.lines()
        .filter(|l| l.contains("STEP") || l.contains("Action:"))
        .enumerate()
        .map(|(i, line)| PlanStep {
            action: format!("step_{}", i),
            tool: tools.first().map(|t| t.name().to_string()),
            reasoning: line.to_string(),
            expected_outcome: "Execute step".to_string(),
        })
        .collect()
}

use std::sync::Arc;
