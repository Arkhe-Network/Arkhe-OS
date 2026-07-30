use async_trait::async_trait;

#[derive(Debug, Clone)]
pub struct Trajectory {
    pub id: String,
    pub agent_id: String,
    pub goal: String,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[async_trait]
pub trait TrajectoryStore: Send + Sync {
    async fn list_trajectories(&self) -> Vec<Trajectory>;
    async fn record_trajectory(
        &self,
        agent_id: &str,
        goal: &str,
        tags: Vec<String>,
        json: &str,
        inputs: Vec<String>,
        outputs: Vec<String>,
    ) -> Result<String, String>;
}

pub struct MemoryStore {}

impl MemoryStore {
    pub fn new() -> Self {
        Self {}
    }
}

#[async_trait]
impl TrajectoryStore for MemoryStore {
    async fn list_trajectories(&self) -> Vec<Trajectory> {
        vec![]
    }

    async fn record_trajectory(
        &self,
        _agent_id: &str,
        _goal: &str,
        _tags: Vec<String>,
        _json: &str,
        _inputs: Vec<String>,
        _outputs: Vec<String>,
    ) -> Result<String, String> {
        Ok(uuid::Uuid::new_v4().to_string())
    }
}

pub type TrajectoryStoreImpl = MemoryStore;
