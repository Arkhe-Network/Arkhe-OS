use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryBucket {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
    pub item_count: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub item_id: String,
    pub bucket_id: String,
    pub title: String,
    pub excerpt: String,
    pub relevance_score: f32,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextItem {
    pub item_id: String,
    pub bucket_id: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub page: usize,
    pub total_pages: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: String,
    pub content: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Conversation {
    pub messages: Vec<Message>,
    pub summary: Option<String>,
}

#[derive(Error, Debug)]
pub enum McpError {
    #[error("Transport error: {0}")]
    Transport(String),
    #[error("Authentication error: {0}")]
    Auth(String),
    #[error("API error: {0}")]
    Api(String),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Bucket not found: {0}")]
    BucketNotFound(String),
    #[error("Rate limited by Plurality, retry after {retry_after:?}")]
    RateLimited { retry_after: Option<chrono::Duration> },
    #[error("Consent revoked for bucket {bucket}")]
    ConsentRevoked { bucket: String },
    #[error("Invalid response from Plurality")]
    InvalidResponse,
    #[error("Invalid JWT: {0}")]
    JwtError(String),
}
