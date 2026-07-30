//! Planejador Hierárquico usando heartbit-core::DagAgent
//!
//! Decompõe objetivos em DAGs de subtarefas atômicas.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use crate::error::CognitiveError;

/// Uma tarefa atômica no plano.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PlanTask {
    pub id: String,
    pub description: String,
    pub tool: String,              // "shell", "http", "python", "simulate"
    pub parameters: serde_json::Value,
    pub requires_approval: bool,   // Se True, precisa de assinatura MultiSig
}

/// Um plano hierárquico: um grafo acíclico dirigido (DAG) de tarefas.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct HierarchicalPlan {
    pub id: String,
    pub goal: String,
    pub tasks: Vec<PlanTask>,
    /// Dependências: (task_id_dependente, task_id_prerequisito)
    /// task_id_dependente depende de task_id_prerequisito
    pub dependencies: Vec<(String, String)>,
}

/// O Planejador Hierárquico que usa LLM para gerar planos estruturados.
pub struct HierarchicalPlanner {
    max_depth: usize,
    max_tasks: usize,
}

impl HierarchicalPlanner {
    pub fn new(max_depth: usize, max_tasks: usize) -> Self {
        Self { max_depth, max_tasks }
    }

    /// Decompõe um objetivo humano em um plano executável.
    ///
    /// Em produção, isto chamaria um LLM (Candle/ONNX) para gerar o plano.
    /// Aqui fornecemos uma implementação determinística para testes.
    pub fn plan(&self, goal: &str, _context: &str) -> Result<HierarchicalPlan, CognitiveError> {
        // TODO: Integrar com LLM real via CandleBackend
        // Por enquanto, gera um plano de exemplo estruturado
        let plan = self.generate_example_plan(goal)?;

        // Validar profundidade
        self.validate_depth(&plan)?;

        // Validar aciclicidade
        self.validate_acyclic(&plan)?;

        // Validar limite de tarefas
        if plan.tasks.len() > self.max_tasks {
            return Err(CognitiveError::PlanGeneration(
                format!("Plan has {} tasks, max allowed is {}", plan.tasks.len(), self.max_tasks)
            ));
        }

        Ok(plan)
    }

    /// Gera um plano de exemplo para demonstração.
    /// Em produção, isto seria substituído por chamada LLM.
    fn generate_example_plan(&self, goal: &str) -> Result<HierarchicalPlan, CognitiveError> {
        let plan_id = format!("plan_{}", uuid::Uuid::new_v4());

        let tasks = vec![
            PlanTask {
                id: "t1".to_string(),
                description: format!("Research phase for: {}", goal),
                tool: "http".to_string(),
                parameters: serde_json::json!({"url": "https://api.example.com/search", "method": "GET"}),
                requires_approval: false,
            },
            PlanTask {
                id: "t2".to_string(),
                description: format!("Analysis phase for: {}", goal),
                tool: "python".to_string(),
                parameters: serde_json::json!({"script": "analyze.py"}),
                requires_approval: true,
            },
            PlanTask {
                id: "t3".to_string(),
                description: format!("Synthesis phase for: {}", goal),
                tool: "shell".to_string(),
                parameters: serde_json::json!({"cmd": "echo 'synthesize'"}),
                requires_approval: false,
            },
        ];

        let dependencies = vec![
            ("t2".to_string(), "t1".to_string()), // t2 depends on t1
            ("t3".to_string(), "t2".to_string()), // t3 depends on t2
        ];

        Ok(HierarchicalPlan {
            id: plan_id,
            goal: goal.to_string(),
            tasks,
            dependencies,
        })
    }

    /// Valida que o plano não excede a profundidade máxima.
    fn validate_depth(&self, plan: &HierarchicalPlan) -> Result<(), CognitiveError> {
        let depth = self.calculate_depth(plan);
        if depth > self.max_depth {
            return Err(CognitiveError::PlanDepthExceeded {
                depth,
                max: self.max_depth,
            });
        }
        Ok(())
    }

    /// Calcula a profundidade máxima do DAG.
    fn calculate_depth(&self, plan: &HierarchicalPlan) -> usize {
        let mut in_degree: HashMap<String, usize> = HashMap::new();
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();

        // Inicializar
        for task in &plan.tasks {
            in_degree.entry(task.id.clone()).or_insert(0);
            adj.entry(task.id.clone()).or_default();
        }

        // Construir grafo
        for (dependent, prerequisite) in &plan.dependencies {
            adj.entry(prerequisite.clone()).or_default().push(dependent.clone());
            *in_degree.entry(dependent.clone()).or_insert(0) += 1;
        }

        // Kahn's algorithm para encontrar caminho mais longo
        let mut queue: Vec<(String, usize)> = in_degree
            .iter()
            .filter(|(_, &d)| d == 0)
            .map(|(id, _)| (id.clone(), 0))
            .collect();

        let mut max_depth = 0;
        let mut visited = HashSet::new();

        while let Some((node, depth)) = queue.pop() {
            if visited.contains(&node) {
                continue;
            }
            visited.insert(node.clone());
            max_depth = max_depth.max(depth);

            if let Some(neighbors) = adj.get(&node) {
                for neighbor in neighbors {
                    queue.push((neighbor.clone(), depth + 1));
                }
            }
        }

        max_depth
    }

    /// Valida que o grafo não contém ciclos.
    fn validate_acyclic(&self, plan: &HierarchicalPlan) -> Result<(), CognitiveError> {
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();
        let mut all_nodes: HashSet<String> = HashSet::new();

        for task in &plan.tasks {
            all_nodes.insert(task.id.clone());
            adj.entry(task.id.clone()).or_default();
        }

        for (dependent, prerequisite) in &plan.dependencies {
            adj.entry(prerequisite.clone()).or_default().push(dependent.clone());
        }

        // DFS com detecção de ciclo (três cores)
        #[derive(Clone, Copy, PartialEq)]
        enum Color { White, Gray, Black }

        let mut colors: HashMap<String, Color> = all_nodes
            .iter()
            .map(|id| (id.clone(), Color::White))
            .collect();

        fn dfs(
            node: &str,
            adj: &HashMap<String, Vec<String>>,
            colors: &mut HashMap<String, Color>,
        ) -> Result<(), CognitiveError> {
            colors.insert(node.to_string(), Color::Gray);

            if let Some(neighbors) = adj.get(node) {
                for neighbor in neighbors {
                    match colors.get(neighbor) {
                        Some(Color::Gray) => return Err(CognitiveError::PlanCycleDetected),
                        Some(Color::White) => dfs(neighbor, adj, colors)?,
                        _ => {}
                    }
                }
            }

            colors.insert(node.to_string(), Color::Black);
            Ok(())
        }

        for node in &all_nodes {
            if colors.get(node) == Some(&Color::White) {
                dfs(node, &adj, &mut colors)?;
            }
        }

        Ok(())
    }

    /// Retorna as tarefas em ordem topológica (prontas para execução).
    pub fn topological_order(&self, plan: &HierarchicalPlan) -> Result<Vec<PlanTask>, CognitiveError> {
        let mut in_degree: HashMap<String, usize> = HashMap::new();
        let mut adj: HashMap<String, Vec<String>> = HashMap::new();
        let mut task_map: HashMap<String, PlanTask> = HashMap::new();

        for task in &plan.tasks {
            in_degree.entry(task.id.clone()).or_insert(0);
            adj.entry(task.id.clone()).or_default();
            task_map.insert(task.id.clone(), task.clone());
        }

        for (dependent, prerequisite) in &plan.dependencies {
            adj.entry(prerequisite.clone()).or_default().push(dependent.clone());
            *in_degree.entry(dependent.clone()).or_insert(0) += 1;
        }

        let mut queue: Vec<String> = in_degree
            .iter()
            .filter(|(_, &d)| d == 0)
            .map(|(id, _)| id.clone())
            .collect();

        let mut result = Vec::new();

        while let Some(node) = queue.pop() {
            if let Some(task) = task_map.get(&node) {
                result.push(task.clone());
            }

            if let Some(neighbors) = adj.get(&node) {
                for neighbor in neighbors {
                    let deg = in_degree.get_mut(neighbor).unwrap();
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push(neighbor.clone());
                    }
                }
            }
        }

        if result.len() != plan.tasks.len() {
            return Err(CognitiveError::PlanCycleDetected);
        }

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plan_depth_validation() {
        let planner = HierarchicalPlanner::new(2, 10);
        let plan = planner.plan("test goal", "context").unwrap();
        assert_eq!(plan.tasks.len(), 3);
    }

    #[test]
    fn test_topological_order() {
        let planner = HierarchicalPlanner::new(5, 10);
        let plan = planner.plan("test", "").unwrap();
        let order = planner.topological_order(&plan).unwrap();
        assert_eq!(order.len(), 3);
        assert_eq!(order[0].id, "t1");
        assert_eq!(order[1].id, "t2");
        assert_eq!(order[2].id, "t3");
    }

    #[test]
    fn test_cycle_detection() {
        let planner = HierarchicalPlanner::new(5, 10);
        let mut plan = planner.plan("test", "").unwrap();
        // Create a cycle: t3 -> t1
        plan.dependencies.push(("t1".to_string(), "t3".to_string()));
        let result = planner.validate_acyclic(&plan);
        assert!(result.is_err());
    }
}
