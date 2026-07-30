use crate::rl::rollout_worker_debate::RolloutExperience;
use crate::rl::config::AsyncRLConfig;

pub struct ReplayBuffer {}

impl ReplayBuffer {
    pub fn new(_config: &AsyncRLConfig) -> Self {
        Self {}
    }

    pub async fn push(&self, _experience: RolloutExperience) {}
    pub async fn sample_batch(&self, _batch_size: usize, _policy_version: u64) -> Vec<RolloutExperience> {
        Vec::new()
    }
    pub async fn update_policy_version(&self, _version: u64) {}
}
