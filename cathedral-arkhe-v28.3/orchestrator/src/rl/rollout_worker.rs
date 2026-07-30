use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RolloutExperience {
    pub reward: f32,
    pub action: String,
    pub timestamp: u64,
}
