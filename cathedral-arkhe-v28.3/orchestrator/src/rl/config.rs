use serde::{Deserialize, Serialize};
// use cathedral_agent::orchestrator::String;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AsyncRLConfig {
    pub train_interval_secs: u64,
    pub num_rollout_workers: usize,
    pub batch_size: usize,
    pub token_budget_per_rollout: u32,
    pub max_steps_per_rollout: usize,
    pub rollout_timeout_secs: u64,
    pub use_fp8_rollout: bool,
    pub step_timeout_secs: u64,
    pub step_delay_ms: u64,
    pub default_reasoning_mode: String,
}
