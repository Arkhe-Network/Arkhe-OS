use thiserror::Error;

#[derive(Debug, Error)]
pub enum UnifiedFsError {
    #[error("Node not found: {path}")]
    NotFound { path: String },

    #[error("Already exists: {path}")]
    AlreadyExists { path: String },

    #[error("Permission denied: {subject} cannot {action} on {path}")]
    PermissionDenied {
        subject: String,
        action: String,
        path: String,
        reason: String,
    },

    #[error("Not a directory: {path}")]
    NotADirectory { path: String },

    #[error("Is a directory: {path}")]
    IsADirectory { path: String },

    #[error("Invalid path: {reason}: {path}")]
    InvalidPath { path: String, reason: String },

    #[error("Path traversal detected: {path}")]
    PathTraversal { path: String },

    #[error("Backend error ({backend}): {message}")]
    Backend { backend: String, message: String },

    #[error("Cross-backend copy failed: {message}")]
    CrossBackendCopy { message: String },

    #[error("Namespace mapping error: {0}")]
    NamespaceMapping(String),

    #[error("Lock conflict: {path}")]
    LockConflict { path: String },

    #[error("Quota exceeded: subject={subject}, used={used}, limit={limit}")]
    QuotaExceeded {
        subject: String,
        used: u64,
        limit: u64,
    },

    #[error("Internal error: {0}")]
    Internal(String),
}

pub type UnifiedFsResult<T> = Result<T, UnifiedFsError>;
