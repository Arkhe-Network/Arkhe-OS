// crates/kernel/src/error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum KernelError {
    #[error("Planning failed: {0}")]
    Planning(String),

    #[error("Execution failed: {0}")]
    Execution(String),

    #[error("Memory operation failed: {0}")]
    Memory(String),

    #[error("System frozen — emergency stop activated")]
    EmergencyStop,

    #[error("Approval required for task {0}")]
    ApprovalRequired(String),

    #[error("Invalid configuration: {0}")]
    Config(String),

    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}
