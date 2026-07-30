//! Cathedral ARKHE v28.3 — PPO/GRPO Trainer Stub
//! Responsável pela atualização da política consumindo experiências do ReplayBuffer.
//!
//! Selo: CATHEDRAL-ARKHE-v28.3-TRAINER-2026-06-16

use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{info, warn};

use crate::rl::rollout_worker::RolloutExperience;

/// Configuração do treinador
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainerConfig {
    pub algorithm: String, // "PPO" ou "GRPO"
    pub learning_rate: f32,
    pub epochs: usize,
    pub clip_ratio: f32,
    pub value_loss_coef: f32,
    pub entropy_coef: f32,
}

impl Default for TrainerConfig {
    fn default() -> Self {
        Self {
            algorithm: "GRPO".to_string(), // Group Relative Policy Optimization (Ling & Ring 2.6)
            learning_rate: 1e-5,
            epochs: 3,
            clip_ratio: 0.2,
            value_loss_coef: 0.1, // GRPO pode usar 0 ou dispensar critic se usar recompensas relativas
            entropy_coef: 0.01,
        }
    }
}

/// Stub para o modelo que será treinado
pub trait PolicyModel: Send + Sync {
    fn update_weights(&self, experiences: &[RolloutExperience]) -> Result<(), String>;
    fn get_version(&self) -> u64;
}

pub struct AsyncTrainer {
    config: TrainerConfig,
    policy_model: Option<Arc<Mutex<dyn PolicyModel>>>, // Opcional no stub
    update_count: u64,
}

impl AsyncTrainer {
    pub fn new(config: TrainerConfig, policy_model: Option<Arc<Mutex<dyn PolicyModel>>>) -> Self {
        Self {
            config,
            policy_model,
            update_count: 0,
        }
    }

    /// Executa uma iteração de treino (update)
    pub async fn train_step(&mut self, batch: Vec<RolloutExperience>) -> Result<(), String> {
        if batch.is_empty() {
            return Ok(());
        }

        self.update_count += 1;

        info!(
            target: "cathedral::async_rl::trainer",
            update_count = self.update_count,
            batch_size = batch.len(),
            algorithm = self.config.algorithm,
            "Iniciando train_step"
        );

        // Lógica GRPO/PPO simulada:
        // 1. Em PPO: Calcular vantagens (GAE), otimizar policy loss (clipada) + value loss.
        // 2. Em GRPO (Group Relative Policy Optimization):
        //    Calcular vantagens relativas dentro do grupo de rollouts (mesmo prompt).
        //    Isso elimina a necessidade de um Critic model separado (Value Model).

        // Apenas simula o tempo de treino
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;

        if let Some(model) = &self.policy_model {
            let model = model.lock().await;
            model.update_weights(&batch)?;
            info!("Pesos do modelo atualizados (versão {})", model.get_version());
        } else {
            // Stub mode
            let avg_reward: f32 = batch.iter().map(|e| e.reward).sum::<f32>() / batch.len() as f32;
            info!(
                target: "cathedral::async_rl::trainer",
                avg_reward = avg_reward,
                "Train step concluído (stub)"
            );
        }

        Ok(())
    }

    pub fn get_update_count(&self) -> u64 {
        self.update_count
    }
}
