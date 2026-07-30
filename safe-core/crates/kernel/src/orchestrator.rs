// crates/kernel/src/orchestrator.rs
//! Orquestrador principal que integra os 3 subsistemas.
//!
//! Usa heartbit-core::Orchestrator para coordenação multi-agente.

use cognitive_core::planner::{HierarchicalPlanner, HierarchicalPlan, PlanTask};
use action_executor::{
    ToolExecutor, SecurityGate, ExecutionGate,
    ShellTool, HttpTool, PythonTool,
};
use memory_system::{
    MerkleSealedVectorStore, VectorEntry, SealedVector,
    MemorySealer, MemorySnapshot,
};
use crate::lifecycle::{SystemLifecycle, SystemState};
use crate::error::KernelError;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{info, warn, error};

/// Configuração do orquestrador.
#[derive(Debug, Clone)]
pub struct OrchestratorConfig {
    pub qdrant_url: String,
    pub qdrant_collection: String,
    pub vector_dimension: u64,
    pub workspace_path: PathBuf,
    pub max_plan_depth: usize,
    pub max_plan_tasks: usize,
}

impl Default for OrchestratorConfig {
    fn default() -> Self {
        Self {
            qdrant_url: "http://localhost:6334".to_string(),
            qdrant_collection: "safe-core-memory".to_string(),
            vector_dimension: 384,
            workspace_path: PathBuf::from("/tmp/safe-core-workspace"),
            max_plan_depth: 5,
            max_plan_tasks: 20,
        }
    }
}

/// Orquestrador principal do Safe-Core AGI.
pub struct SafeCoreOrchestrator {
    lifecycle: Arc<RwLock<SystemLifecycle>>,
    planner: HierarchicalPlanner,
    executor: Arc<RwLock<ToolExecutor>>,
    memory: Option<Arc<MerkleSealedVectorStore>>,
    sealer: MemorySealer,
    config: OrchestratorConfig,
}

impl SafeCoreOrchestrator {
    pub async fn new(config: OrchestratorConfig) -> Result<Self, KernelError> {
        let lifecycle = Arc::new(RwLock::new(SystemLifecycle::new()));

        let planner = HierarchicalPlanner::new(config.max_plan_depth, config.max_plan_tasks);

        let mut executor = ToolExecutor::new();

        // Configurar gates de segurança
        let security_gate = SecurityGate {
            allowed_schemes: vec!["https".into()],
            allowed_domains: vec!["api.github.com".into(), "api.openai.com".into()],
            max_response_size: 10 * 1024 * 1024,
            timeout_secs: 30,
            allowed_binaries: vec!["python3".into(), "bash".into(), "sh".into()],
            read_paths: vec!["/usr".into(), "/lib".into()],
            write_paths: vec![config.workspace_path.clone()],
        };

        let execution_gate = ExecutionGate::new(
            security_gate,
            config.workspace_path.clone(),
        );

        // Registrar ferramentas
        executor.register_tool(Box::new(ShellTool::new(execution_gate.clone())));
        executor.register_tool(Box::new(HttpTool::new(execution_gate.clone())));
        executor.register_tool(Box::new(PythonTool::new(execution_gate)));

        // Inicializar memória
        let memory = MerkleSealedVectorStore::new(
            &config.qdrant_url,
            &config.qdrant_collection,
            config.vector_dimension,
        ).await.map_err(|e| KernelError::Memory(e.to_string()))?;

        let sealer = MemorySealer::new("safe-core-memory-key".to_string());

        {
            let mut lifecycle = lifecycle.write().await;
            lifecycle.transition(SystemState::Ready)?;
        }

        Ok(Self {
            lifecycle,
            planner,
            executor: Arc::new(RwLock::new(executor)),
            memory: Some(Arc::new(memory)),
            sealer,
            config,
        })
    }

    /// Ciclo principal: Planejar → Executar → Selar.
    pub async fn execute_task(&self, goal: &str, context: &str) -> Result<TaskExecutionReport, KernelError> {
        // 1. Verificar estado
        {
            let lifecycle = self.lifecycle.read().await;
            if lifecycle.is_frozen() {
                return Err(KernelError::EmergencyStop);
            }
        }

        // 2. PLANEJAR
        info!("Planning task: {}", goal);
        {
            let mut lifecycle = self.lifecycle.write().await;
            lifecycle.transition(SystemState::Planning)?;
        }

        let plan = self.planner.plan(goal, context)
            .map_err(|e| KernelError::Planning(e.to_string()))?;

        info!("Plan generated: {} tasks", plan.tasks.len());

        // 3. EXECUTAR
        {
            let mut lifecycle = self.lifecycle.write().await;
            lifecycle.transition(SystemState::Executing)?;
        }

        let executor = self.executor.read().await;
        let execution_results = executor.execute_plan(&plan).await
            .map_err(|e| KernelError::Execution(e.to_string()))?;

        info!("Execution complete: {} results", execution_results.len());

        // 4. SELAR (Memória)
        {
            let mut lifecycle = self.lifecycle.write().await;
            lifecycle.transition(SystemState::Sealing)?;
        }

        if let Some(memory) = &self.memory {
            for result in &execution_results {
                let embedding = self.generate_embedding(&result.result.stdout);

                let entry = VectorEntry {
                    id: format!("exec_{}_{}", result.task_id, uuid::Uuid::new_v4()),
                    vector: embedding,
                    metadata: serde_json::json!({
                        "task_id": result.task_id,
                        "stdout": result.result.stdout,
                        "stderr": result.result.stderr,
                        "exit_code": result.result.exit_code,
                        "approved": result.approved,
                    }),
                    timestamp: chrono::Utc::now().timestamp(),
                };

                memory.insert(entry).await
                    .map_err(|e| KernelError::Memory(e.to_string()))?;
            }

            // Criar snapshot selado
            let snapshot = self.sealer.create_snapshot(memory).await
                .map_err(|e| KernelError::Memory(e.to_string()))?;

            info!("Memory sealed: root={}, size={}",
                hex::encode(snapshot.root_hash), snapshot.tree_size);
        }

        // 5. Retornar ao estado Ready
        {
            let mut lifecycle = self.lifecycle.write().await;
            lifecycle.transition(SystemState::Ready)?;
        }

        Ok(TaskExecutionReport {
            plan,
            results: execution_results.into_iter().map(|r| r.result).collect(),
            sealed: true,
        })
    }

    /// Congela o sistema (emergência).
    pub async fn emergency_freeze(&self) {
        let mut lifecycle = self.lifecycle.write().await;
        lifecycle.freeze();

        let mut executor = self.executor.write().await;
        executor.freeze();

        error!("SYSTEM EMERGENCY FREEZE — all operations halted");
    }

    /// Gera embedding dummy (placeholder para modelo real).
    fn generate_embedding(&self, text: &str) -> Vec<f32> {
        // TODO: Integrar com candle-transformers para embeddings reais
        // Por enquanto: hash determinístico como embedding dummy
        use sha2::{Sha256, Digest};
        let hash = Sha256::digest(text.as_bytes());
        let dim = self.config.vector_dimension as usize;
        let mut embedding = Vec::with_capacity(dim);
        for i in 0..dim {
            let byte = hash[i % hash.len()];
            embedding.push((byte as f32 / 255.0) * 2.0 - 1.0);
        }
        embedding
    }

    /// Retorna estado atual.
    pub async fn state(&self) -> SystemState {
        let lifecycle = self.lifecycle.read().await;
        lifecycle.state()
    }
}

/// Relatório de execução de tarefa.
#[derive(Debug, Clone)]
pub struct TaskExecutionReport {
    pub plan: HierarchicalPlan,
    pub results: Vec<action_executor::tools::ToolResult>,
    pub sealed: bool,
}
