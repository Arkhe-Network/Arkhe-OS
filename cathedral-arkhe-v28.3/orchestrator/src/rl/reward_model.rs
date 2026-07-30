use async_trait::async_trait;

#[async_trait]
pub trait RewardModel: Send + Sync {
    async fn compute_reward(&self, observation: &str, action: &str) -> Result<f32, String>;
    async fn update_with_feedback(&self, observation: &str, action: &str, human_rating: f32) -> Result<(), String>;
}
