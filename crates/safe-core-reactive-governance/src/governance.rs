use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GovernanceAction {
    RollbackCurriculum {
        target_sth: Vec<u8>,
        reason: String,
    },
    AdjustTeacherReward {
        teacher_id: String,
        environment_hash: String,
        reward_delta: f64,
        reason: String,
    },
    BanRoutingPath {
        router_id: String,
        from_module: String,
        to_module: String,
        reason: String,
    },
    EmergencyFreeze {
        reason: String,
        duration_seconds: u64,
    },
    Unfreeze {
        reason: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GovernanceEntry {
    pub action: GovernanceAction,
    pub issued_by: String,
    pub timestamp: i64,
    pub signature: Vec<u8>,
    pub verifying_key: Vec<u8>,
}

#[derive(Debug, thiserror::Error)]
pub enum GovernanceError {
    #[error("Serialization error: {0}")]
    Serialization(String),
    #[error("Invalid signature: {0}")]
    InvalidSignature(String),
    #[error("Unauthorized issuer: {0}")]
    Unauthorized(String),
    #[error("Governance action not supported: {0}")]
    UnsupportedAction(String),
}

pub type GovernanceResult<T> = Result<T, GovernanceError>;
