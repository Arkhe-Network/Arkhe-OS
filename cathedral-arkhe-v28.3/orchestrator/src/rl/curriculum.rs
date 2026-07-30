//! Cathedral ARKHE v28.3 — Curriculum de Tarefas
//! Gerencia metas de rollout, aumentando progressivamente a dificuldade.
//!
//! Selo: CATHEDRAL-ARKHE-v28.3-CURRICULUM-2026-06-16

use serde::{Deserialize, Serialize};

/// Nível de dificuldade de uma tarefa
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub enum Difficulty {
    Beginner = 1,
    Intermediate = 2,
    Advanced = 3,
    Expert = 4,
}

/// Tarefa do currículo
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskDef {
    pub id: String,
    pub prompt: String,
    pub difficulty: Difficulty,
    pub required_skills: Vec<String>,
}

pub struct CurriculumManager {
    tasks: Vec<TaskDef>,
    current_difficulty: Difficulty,
    success_rate: f32, // Para promoção
}

impl CurriculumManager {
    pub fn new() -> Self {
        Self {
            tasks: Self::default_tasks(),
            current_difficulty: Difficulty::Beginner,
            success_rate: 0.0,
        }
    }

    /// Retorna as próximas tarefas adequadas à dificuldade atual
    pub fn get_next_tasks(&self, count: usize) -> Vec<String> {
        let available: Vec<_> = self.tasks.iter()
            .filter(|t| t.difficulty <= self.current_difficulty)
            .collect();

        // Simples round-robin/random (aqui pega os primeiros)
        available.into_iter()
            .take(count)
            .map(|t| t.prompt.clone())
            .collect()
    }

    /// Atualiza taxa de sucesso e promove dificuldade se necessário
    pub fn update_success_rate(&mut self, new_rate: f32) {
        // Suavização exponencial simples
        self.success_rate = 0.8 * self.success_rate + 0.2 * new_rate;

        if self.success_rate > 0.85 {
            self.promote_difficulty();
        }
    }

    fn promote_difficulty(&mut self) {
        self.current_difficulty = match self.current_difficulty {
            Difficulty::Beginner => Difficulty::Intermediate,
            Difficulty::Intermediate => Difficulty::Advanced,
            Difficulty::Advanced => Difficulty::Expert,
            Difficulty::Expert => Difficulty::Expert,
        };
        tracing::info!("Curriculum promovido para {:?}", self.current_difficulty);
    }

    fn default_tasks() -> Vec<TaskDef> {
        vec![
            TaskDef {
                id: "t1".to_string(),
                prompt: "Analyze the current market trends for DeFi yields.".to_string(),
                difficulty: Difficulty::Beginner,
                required_skills: vec!["web_search".to_string()],
            },
            TaskDef {
                id: "t2".to_string(),
                prompt: "Identify the top 3 liquidity pools with the highest APR.".to_string(),
                difficulty: Difficulty::Beginner,
                required_skills: vec!["picoads".to_string()],
            },
            TaskDef {
                id: "t3".to_string(),
                prompt: "Evaluate the risk of impermanent loss and propose a mitigation strategy.".to_string(),
                difficulty: Difficulty::Intermediate,
                required_skills: vec!["analysis".to_string()],
            },
            TaskDef {
                id: "t4".to_string(),
                prompt: "Write a script to aggregate yields from multiple EVM chains and execute trades.".to_string(),
                difficulty: Difficulty::Advanced,
                required_skills: vec!["code_execution".to_string()],
            },
        ]
    }
}
