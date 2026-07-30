use cathedral_mcp_client::{PluralityMcpClient, SearchResult, MemoryBucket, McpError};
use crate::cache::MemoryCache;
use std::collections::HashMap;
use tracing::debug;
use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MemoryLevel {
    M0Cache,
    M1Work,
    M2Episodic,
    M3Semantic,
    M4Procedural,
}

pub struct MemoryBlock {
    pub key: String,
    pub content: Vec<u8>,
    pub metadata: HashMap<String, String>,
    pub level: MemoryLevel,
}

#[derive(Error, Debug)]
pub enum AdapterError {
    #[error("MCP error: {0}")]
    Mcp(#[from] McpError),
    #[error("Cache error: {0}")]
    Cache(String),
    #[error("Level {0:?} not supported for Plurality")]
    UnsupportedLevel(MemoryLevel),
    #[error("Content not found")]
    NotFound,
}

pub struct PluralityMemoryAdapter {
    client: PluralityMcpClient,
    cache: MemoryCache,
    bucket_mapping: HashMap<MemoryLevel, String>,
    default_bucket: String,
}

impl PluralityMemoryAdapter {
    pub async fn new(
        client: PluralityMcpClient,
        cache_capacity: usize,
        cache_ttl_seconds: u64,
        mapping: HashMap<MemoryLevel, String>,
        default_bucket: String,
    ) -> Self {
        Self {
            client,
            cache: MemoryCache::new(cache_capacity, cache_ttl_seconds),
            bucket_mapping: mapping,
            default_bucket,
        }
    }

    fn map_level_to_bucket(&self, level: MemoryLevel) -> &str {
        self.bucket_mapping.get(&level)
            .map(|s| s.as_str())
            .unwrap_or(&self.default_bucket)
    }

    pub async fn read(&self, key: &str, level: MemoryLevel) -> Result<Option<Vec<u8>>, AdapterError> {
        if level == MemoryLevel::M0Cache || level == MemoryLevel::M1Work {
            if let Some(cached) = self.cache.get(key).await {
                debug!("Cache hit for key: {}", key);
                return Ok(Some(cached));
            }
        }

        if level == MemoryLevel::M2Episodic || level == MemoryLevel::M3Semantic {
            let _bucket_id = self.map_level_to_bucket(level);
            let results = self.client.search_memory(key, 1).await?;
            if let Some(result) = results.first() {
                let item = self.client.read_context(&result.item_id, 0).await?;
                let content_bytes = item.content.into_bytes();
                if level == MemoryLevel::M0Cache || level == MemoryLevel::M1Work {
                    self.cache.set(key.to_string(), content_bytes.clone()).await;
                }
                return Ok(Some(content_bytes));
            }
            return Ok(None);
        }

        Err(AdapterError::UnsupportedLevel(level))
    }

    pub async fn write(&self, key: &str, content: &[u8], level: MemoryLevel) -> Result<(), AdapterError> {
        if level == MemoryLevel::M4Procedural {
            return Err(AdapterError::UnsupportedLevel(level));
        }

        let bucket_id = self.map_level_to_bucket(level);
        let content_str = String::from_utf8_lossy(content);
        self.client.save_memory(bucket_id, &content_str, Some(key)).await?;

        if level == MemoryLevel::M0Cache || level == MemoryLevel::M1Work {
            self.cache.set(key.to_string(), content.to_vec()).await;
        }

        Ok(())
    }

    pub async fn search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>, AdapterError> {
        Ok(self.client.search_memory(query, limit).await?)
    }

    pub async fn list_buckets(&self) -> Result<Vec<MemoryBucket>, AdapterError> {
        Ok(self.client.get_user_memory_buckets().await?)
    }

    pub async fn create_bucket(&self, name: &str, description: Option<&str>) -> Result<String, AdapterError> {
        Ok(self.client.create_memory_bucket(name, description).await?)
    }

    pub async fn save_conversation(
        &self,
        bucket_id: &str,
        messages: Vec<cathedral_mcp_client::Message>,
        summary: Option<&str>,
    ) -> Result<(), AdapterError> {
        Ok(self.client.save_conversation(bucket_id, messages, summary).await?)
    }
}
