use async_trait::async_trait;
// use cathedral_agent::orchestrator::String;
use crate::rl::reward_model::RewardModel;

pub struct DebateConsensusRewardModel {}

impl DebateConsensusRewardModel {
    pub fn new() -> Self {
        Self {}
    }

    pub async fn compute_consensus_reward(&self, _agent_id: &String, _observation: &str, _action: &str) -> Result<f32, String> {
        Ok(0.0)
    }
}

#[async_trait]
impl RewardModel for DebateConsensusRewardModel {
    async fn compute_reward(&self, _observation: &str, _action: &str) -> Result<f32, String> {
        Ok(0.0)
    }

    async fn update_with_feedback(&self, _observation: &str, _action: &str, _human_rating: f32) -> Result<(), String> {
        Ok(())
    }
}
