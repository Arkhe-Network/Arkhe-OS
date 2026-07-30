//! Executor de tarefas com gates de segurança

use cognitive_core::planner::{HierarchicalPlan, PlanTask};
use crate::error::ExecError;
use crate::tools::{Tool, ToolResult};
use std::collections::HashMap;
use tracing::{info, warn, error};

/// Executor de tarefas que recebe um plano e executa respeitando gates.
pub struct ToolExecutor {
    tools: HashMap<String, Box<dyn Tool>>,
    frozen: bool,
}

impl ToolExecutor {
    pub fn new() -> Self {
        Self {
            tools: HashMap::new(),
            frozen: false,
        }
    }

    pub fn register_tool(&mut self, tool: Box<dyn Tool>) {
        self.tools.insert(tool.name().to_string(), tool);
    }

    /// Verifica se o sistema está congelado.
    pub fn is_frozen(&self) -> bool {
        self.frozen
    }

    /// Congela o sistema (emergência).
    pub fn freeze(&mut self) {
        self.frozen = true;
        error!("SYSTEM FROZEN — no further actions allowed");
    }

    /// Descongela o sistema.
    pub fn thaw(&mut self) {
        self.frozen = false;
        info!("SYSTEM THAWED — actions resumed");
    }

    /// Executa um plano hierárquico completo.
    pub async fn execute_plan(&self, plan: &HierarchicalPlan) -> Result<Vec<TaskExecution>, ExecError> {
        if self.frozen {
            return Err(ExecError::NotImplemented("System frozen".into()));
        }

        let mut results = Vec::new();

        // Executar tarefas em ordem topológica
        // (simplificado: assume ordem linear por enquanto)
        for task in &plan.tasks {
            match self.execute_task(task).await {
                Ok(result) => {
                    info!("Task {} executed successfully", task.id);
                    results.push(TaskExecution {
                        task_id: task.id.clone(),
                        result,
                        approved: !task.requires_approval,
                    });
                }
                Err(e) => {
                    error!("Task {} failed: {}", task.id, e);
                    return Err(e);
                }
            }
        }

        Ok(results)
    }

    /// Executa uma única tarefa.
    pub async fn execute_task(&self, task: &PlanTask) -> Result<ToolResult, ExecError> {
        if self.frozen {
            return Err(ExecError::NotImplemented("System frozen".into()));
        }

        let tool = self.tools.get(&task.tool)
            .ok_or_else(|| ExecError::ToolNotFound(task.tool.clone()))?;

        // Se requer aprovação, verificar (placeholder)
        if task.requires_approval {
            warn!("Task {} requires approval — executing with elevated trust", task.id);
            // TODO: Integrar com sistema de aprovação MultiSig
        }

        tool.execute(&task.parameters).await
    }
}

impl Default for ToolExecutor {
    fn default() -> Self {
        Self::new()
    }
}

/// Resultado da execução de uma tarefa no plano.
#[derive(Debug, Clone)]
pub struct TaskExecution {
    pub task_id: String,
    pub result: ToolResult,
    pub approved: bool,
}
