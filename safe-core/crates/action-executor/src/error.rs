use thiserror::Error;

#[derive(Debug, Error)]
pub enum ExecError {
    #[error("Binary '{0}' not in allowed whitelist")]
    BinaryNotAllowed(String),

    #[error("Command parse failed: {0}")]
    Parse(String),

    #[error("IO error: {0}")]
    Io(String),

    #[error("Fork failed: {0}")]
    Fork(String),

    #[error("Execution timeout after {0}s")]
    Timeout(u64),

    #[error("Child process killed (SIGKILL)")]
    Killed,

    #[error("Invalid URL: {0}")]
    InvalidUrl(String),

    #[error("URL scheme '{0}' not allowed")]
    ForbiddenScheme(String),

    #[error("Domain '{0}' not in whitelist")]
    ForbiddenDomain(String),

    #[error("Response too large: {size} bytes (max: {max})")]
    Oversized { size: usize, max: usize },

    #[error("Invalid HTTP method: {0}")]
    InvalidMethod(String),

    #[error("HTTP error: {0}")]
    Http(String),

    #[error("Landlock sandbox error: {0}")]
    Landlock(String),

    #[error("Tool '{0}' not found")]
    ToolNotFound(String),

    #[error("Parameter '{0}' missing")]
    MissingParam(String),

    #[error("Not implemented: {0}")]
    NotImplemented(String),
}

impl From<std::io::Error> for ExecError {
    fn from(e: std::io::Error) -> Self {
        ExecError::Io(e.to_string())
    }
}

impl From<reqwest::Error> for ExecError {
    fn from(e: reqwest::Error) -> Self {
        ExecError::Http(e.to_string())
    }
}
