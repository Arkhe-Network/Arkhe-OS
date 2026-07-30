//! Cathedral ARKHE v28.3 — Async Rollout Worker com Debate Nativo

use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::{Mutex, Semaphore};
use tokio::task::JoinSet;
use tracing::{debug, error, info, warn};
use serde::{Deserialize, Serialize};

// use cathedral_agent::agent_loop::CathedralAgent;
// use cathedral_agent::orchestrator::{String, String};
use crate::rl::replay_buffer::ReplayBuffer;
use crate::rl::reward_model::RewardModel;
use crate::rl::debate_rewards::DebateConsensusRewardModel;
use crate::rl::config::AsyncRLConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RolloutExperience {
    pub agent_id: String,
    pub observation: String,
    pub action: String,
    pub reward: f32,
    pub next_observation: Option<String>,
    pub done: bool,
    pub policy_version: u64,
    pub timestamp: u64,
    pub tokens_used: u32,
    pub reasoning_mode: String,
    pub tool_calls_count: u32,
}

pub struct RolloutWorkerState {
    pub agent: Arc<Mutex<dyn core::any::Any + Send + Sync>>,
    pub buffer: Arc<ReplayBuffer>,
    pub reward_model: Arc<dyn RewardModel>,
    pub debate_reward_model: Option<Arc<DebateConsensusRewardModel>>,
    pub config: AsyncRLConfig,
    pub worker_id: usize,
    pub policy_version: u64,
    pub total_rollouts: usize,
    pub total_steps: usize,
}

pub struct AsyncRolloutWorker {
    pub state: Arc<Mutex<RolloutWorkerState>>,
    pub semaphore: Arc<Semaphore>,
}

impl AsyncRolloutWorker {
    pub fn new(
        agent: Arc<Mutex<dyn core::any::Any + Send + Sync>>,
        buffer: Arc<ReplayBuffer>,
        reward_model: Arc<dyn RewardModel>,
        debate_reward_model: Option<Arc<DebateConsensusRewardModel>>,
        config: AsyncRLConfig,
        worker_id: usize,
    ) -> Self {
        let state = RolloutWorkerState {
            agent,
            buffer,
            reward_model,
            debate_reward_model,
            config: config.clone(),
            worker_id,
            policy_version: 0,
            total_rollouts: 0,
            total_steps: 0,
        };
        let semaphore = Arc::new(Semaphore::new(config.num_rollout_workers));
        Self {
            state: Arc::new(Mutex::new(state)),
            semaphore,
        }
    }

    pub async fn run_rollout_loop(
        &self,
        initial_goal: &str,
        token_budget: u32,
        max_steps: usize,
    ) -> Result<Vec<RolloutExperience>, String> {
        let _permit = self.semaphore.acquire().await
            .map_err(|e| format!("Semaphore acquire error: {}", e))?;

        let mut state = self.state.lock().await;
        let policy_version = state.policy_version;

        let mut experiences = Vec::new();
        let mut tokens_used = 0;
        let mut observation = initial_goal.to_string();
        let mut done = false;
        let mut step_count = 0;
        let start_time = Instant::now();

        let step_timeout = Duration::from_secs(state.config.step_timeout_secs);

        while tokens_used < token_budget && step_count < max_steps && !done {
            step_count += 1;

            let step_result = tokio::time::timeout(
                step_timeout,
                self.execute_step(&mut state, &observation, policy_version),
            ).await.map_err(|_| format!("Step {} timeout", step_count))?;

            let (action, reward, next_obs, done_flag, tokens) = step_result?;

            let exp = RolloutExperience {
                agent_id: format!("worker_{}", state.worker_id),
                observation: observation.clone(),
                action: action.clone(),
                reward,
                next_observation: Some(next_obs.clone()),
                done: done_flag,
                policy_version,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs(),
                tokens_used: tokens,
                reasoning_mode: state.config.default_reasoning_mode.clone(),
                tool_calls_count: 0,
            };

            tokens_used += tokens;
            observation = next_obs;
            done = done_flag;

            state.buffer.push(exp.clone()).await;
            experiences.push(exp);
            state.total_steps += 1;

            tokio::time::sleep(Duration::from_millis(state.config.step_delay_ms)).await;
        }

        state.total_rollouts += 1;
        Ok(experiences)
    }

    async fn execute_step(
        &self,
        state: &mut RolloutWorkerState,
        observation: &str,
        policy_version: u64,
    ) -> Result<(String, f32, String, bool, u32), String> {
        let mut agent = state.agent.lock().await;
        let action = "dummy action".to_string();
        let tokens = 10;

        let reward = if let Some(debate_model) = &state.debate_reward_model {
            let agent_id = format!("worker_{}", state.worker_id);
            debate_model.compute_consensus_reward(&agent_id, observation, &action).await
                .unwrap_or_else(|_| 0.0) // fallback simple here
        } else {
            state.reward_model.compute_reward(observation, &action).await
                .map_err(|e| format!("Reward model error: {}", e))?
        };

        let done = action.to_lowercase().contains("finalizado")
            || action.to_lowercase().contains("concluído")
            || action.to_lowercase().contains("done");

        let next_obs = action.clone();
        state.policy_version = policy_version;

        Ok((action, reward, next_obs, done, tokens))
    }

    pub async fn update_policy_version(&self, version: u64) {
        let mut state = self.state.lock().await;
        state.policy_version = version;
    }

    pub async fn stats(&self) -> RolloutStats {
        let state = self.state.lock().await;
        RolloutStats {
            worker_id: state.worker_id,
            total_rollouts: state.total_rollouts,
            total_steps: state.total_steps,
            current_policy_version: state.policy_version,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RolloutStats {
    pub worker_id: usize,
    pub total_rollouts: usize,
    pub total_steps: usize,
    pub current_policy_version: u64,
}

pub struct RolloutManager {
    workers: Vec<AsyncRolloutWorker>,
    config: AsyncRLConfig,
}

impl RolloutManager {
    pub fn new(
        agent: Arc<Mutex<dyn core::any::Any + Send + Sync>>,
        buffer: Arc<ReplayBuffer>,
        reward_model: Arc<dyn RewardModel>,
        debate_reward_model: Option<Arc<DebateConsensusRewardModel>>,
        config: AsyncRLConfig,
    ) -> Self {
        let mut workers = Vec::with_capacity(config.num_rollout_workers);
        for i in 0..config.num_rollout_workers {
            let worker = AsyncRolloutWorker::new(
                agent.clone(),
                buffer.clone(),
                reward_model.clone(),
                debate_reward_model.clone(),
                config.clone(),
                i,
            );
            workers.push(worker);
        }
        Self { workers, config }
    }

    pub async fn run_parallel_rollouts(
        &mut self,
        goals: Vec<String>,
        token_budget: u32,
        max_steps: usize,
    ) -> Result<Vec<Vec<RolloutExperience>>, String> {
        let mut join_set = JoinSet::new();
        let worker_goals: Vec<(usize, String)> = goals.into_iter()
            .enumerate()
            .map(|(i, goal)| (i % self.workers.len(), goal))
            .collect();

        for (worker_idx, goal) in worker_goals {
            let worker = self.workers[worker_idx].clone();
            let budget = token_budget;
            let steps = max_steps;
            join_set.spawn(async move {
                worker.run_rollout_loop(&goal, budget, steps).await
            });
        }

        let mut results = Vec::with_capacity(join_set.len());
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(experiences)) => results.push(experiences),
                Ok(Err(e)) => return Err(format!("Rollout worker error: {}", e)),
                Err(e) => return Err(format!("Join error: {}", e)),
            }
        }
        Ok(results)
    }

    pub async fn update_all_policy_versions(&self, version: u64) {
        for worker in &self.workers {
            worker.update_policy_version(version).await;
        }
    }

    pub async fn all_stats(&self) -> Vec<RolloutStats> {
        let mut stats = Vec::with_capacity(self.workers.len());
        for worker in &self.workers {
            stats.push(worker.stats().await);
        }
        stats
    }
}

impl Clone for AsyncRolloutWorker {
    fn clone(&self) -> Self {
        Self {
            state: self.state.clone(),
            semaphore: self.semaphore.clone(),
        }
    }
}
