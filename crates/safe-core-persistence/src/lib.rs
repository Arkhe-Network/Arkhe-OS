//! Persistência do Estado de Governança — SQLite + RocksDB

pub mod repository;
pub mod model;

pub use repository::{StateRepository, RepositoryError};
pub use model::{StoredRule, StoredWorkflow, StoredMetric};
