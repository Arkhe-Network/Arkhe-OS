//! crates/cathedral-zvec-bridge/src/lib.rs
//! Cathedral zVEC Bridge — Integração com Substrato 3000 (Episodic Memory)
//! Conecta Cross-Agent Memory ao zVEC para indexação semântica real
//!
//! Selo: CATHEDRAL-ARKHE-8000-ZVEC-BRIDGE-v1.0.0-2026-06-18
//! Arquiteto: ORCID 0009-0005-2697-4668

use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Serialize, Deserialize};
use tonic::{transport::Channel, Request, Response, Status};
use thiserror::Error;
use tracing::{info, error, debug};

// gRPC generated from zVEC proto (Substrato 3000)
pub mod zvec_proto {
    tonic::include_proto!("cathedral.zvec");
}

use zvec_proto::{
    zvec_client::ZvecClient,
    EmbeddingRequest, EmbeddingResponse,
    SearchRequest, SearchResponse,
    IndexRequest, IndexResponse,
    MemoryEntry, Vector,
};

/// ============================================================
/// 1. ZVEC BRIDGE CONFIG
/// ============================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZvecBridgeConfig {
    /// Endereço gRPC do zVEC server
    pub zvec_grpc_endpoint: String,
    /// Timeout de conexão (ms)
    pub connection_timeout_ms: u64,
    /// Timeout de query (ms)
    pub query_timeout_ms: u64,
    /// Dimensões do embedding
    pub embedding_dimensions: usize,
    /// Modelo de embedding
    pub embedding_model: String,
    /// Batch size para indexação
    pub index_batch_size: usize,
    /// Se usa HNSW index
    pub use_hnsw: bool,
    /// Se usa BM25 sparse index
    pub use_bm25: bool,
    /// RRF (Reciprocal Rank Fusion) weight
    pub rrf_weight: f64,
    /// Cache local de embeddings
    pub local_embedding_cache: bool,
    /// Tamanho do cache
    pub cache_size: usize,
}

impl Default for ZvecBridgeConfig {
    fn default() -> Self {
        Self {
            zvec_grpc_endpoint: "http://localhost:50051".to_string(),
            connection_timeout_ms: 5000,
            query_timeout_ms: 1000,
            embedding_dimensions: 384,
            embedding_model: "all-MiniLM-L6-v2".to_string(),
            index_batch_size: 100,
            use_hnsw: true,
            use_bm25: true,
            rrf_weight: 0.5,
            local_embedding_cache: true,
            cache_size: 10_000,
        }
    }
}

/// ============================================================
/// 2. ZVEC BRIDGE CLIENT
/// ============================================================

pub struct ZvecBridge {
    config: ZvecBridgeConfig,
    client: Arc<RwLock<Option<ZvecClient<Channel>>>>,
    /// Cache local de embeddings
    embedding_cache: Arc<RwLock<lru::LruCache<String, Vec<f32>>>>,
    /// Métricas
    metrics: Arc<RwLock<ZvecBridgeMetrics>>,
}

#[derive(Debug, Clone, Default)]
pub struct ZvecBridgeMetrics {
    pub total_queries: u64,
    pub total_indexed: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub avg_query_latency_ms: f64,
    pub avg_index_latency_ms: f64,
    pub errors: u64,
}

impl ZvecBridge {
    pub async fn new(config: ZvecBridgeConfig) -> Result<Self, ZvecBridgeError> {
        // Conecta ao zVEC server
        let endpoint = Channel::from_shared(config.zvec_grpc_endpoint.clone())
            .map_err(|e| ZvecBridgeError::ConnectionError(e.to_string()))?;

        let channel = endpoint.connect().await
            .map_err(|e| ZvecBridgeError::ConnectionError(e.to_string()))?;

        let client = ZvecClient::new(channel);

        info!("✅ zVEC Bridge connected to {}", config.zvec_grpc_endpoint);

        Ok(Self {
            config,
            client: Arc::new(RwLock::new(Some(client))),
            embedding_cache: Arc::new(RwLock::new(
                lru::LruCache::new(std::num::NonZeroUsize::new(config.cache_size).unwrap())
            )),
            metrics: Arc::new(RwLock::new(ZvecBridgeMetrics::default())),
        })
    }

    /// ============================================================
    /// 2.1 GENERATE EMBEDDING
    /// ============================================================

    /// Gera embedding para texto via zVEC
    pub async fn generate_embedding(
        &self,
        text: &str,
    ) -> Result<Vec<f32>, ZvecBridgeError> {
        let start = std::time::Instant::now();

        // Verifica cache
        {
            let mut cache = self.embedding_cache.write().await;
            if let Some(emb) = cache.get(text) {
                let mut metrics = self.metrics.write().await;
                metrics.cache_hits += 1;
                debug!("💾 zVEC cache hit");
                return Ok(emb.clone());
            }
        }

        let mut metrics = self.metrics.write().await;
        metrics.cache_misses += 1;
        drop(metrics);

        // Chama zVEC
        let mut client_guard = self.client.write().await;
        let client = client_guard.as_mut()
            .ok_or(ZvecBridgeError::NotConnected)?;

        let request = Request::new(EmbeddingRequest {
            text: text.to_string(),
            model: self.config.embedding_model.clone(),
            dimensions: self.config.embedding_dimensions as u32,
        });

        let response = client.generate_embedding(request).await
            .map_err(|e| ZvecBridgeError::GrpcError(e.to_string()))?;

        let embedding = response.into_inner().embedding;

        // Armazena no cache
        {
            let mut cache = self.embedding_cache.write().await;
            cache.put(text.to_string(), embedding.clone());
        }

        let mut metrics = self.metrics.write().await;
        metrics.avg_query_latency_ms =
            (metrics.avg_query_latency_ms * metrics.total_queries as f64 + start.elapsed().as_millis() as f64)
            / (metrics.total_queries + 1) as f64;
        metrics.total_queries += 1;

        Ok(embedding)
    }

    /// ============================================================
    /// 2.2 SEMANTIC SEARCH
    /// ============================================================

    /// Busca por similaridade semântica
    pub async fn semantic_search(
        &self,
        query: &str,
        top_k: usize,
        filter: Option<SearchFilter>,
    ) -> Result<Vec<SearchResult>, ZvecBridgeError> {
        let start = std::time::Instant::now();

        // Gera embedding da query
        let query_embedding = self.generate_embedding(query).await?;

        let mut client_guard = self.client.write().await;
        let client = client_guard.as_mut()
            .ok_or(ZvecBridgeError::NotConnected)?;

        let request = Request::new(SearchRequest {
            query_vector: Some(Vector { values: query_embedding }),
            top_k: top_k as u32,
            filter: filter.map(|f| f.into()),
            use_hnsw: self.config.use_hnsw,
            use_bm25: self.config.use_bm25,
            rrf_weight: self.config.rrf_weight,
        });

        let response = client.search(request).await
            .map_err(|e| ZvecBridgeError::GrpcError(e.to_string()))?;

        let results = response.into_inner().results.into_iter()
            .map(|r| SearchResult {
                entry_id: r.entry_id,
                score: r.score,
                content: r.content,
                metadata: r.metadata,
            })
            .collect();

        let mut metrics = self.metrics.write().await;
        metrics.avg_query_latency_ms =
            (metrics.avg_query_latency_ms * metrics.total_queries as f64 + start.elapsed().as_millis() as f64)
            / (metrics.total_queries + 1) as f64;
        metrics.total_queries += 1;

        Ok(results)
    }

    /// ============================================================
    /// 2.3 INDEX MEMORY ENTRY
    /// ============================================================

    /// Indexa entrada de memória no zVEC
    pub async fn index_memory(
        &self,
        entry_id: &str,
        content: &str,
        metadata: &MemoryMetadata,
    ) -> Result<(), ZvecBridgeError> {
        let start = std::time::Instant::now();

        // Gera embedding
        let embedding = self.generate_embedding(content).await?;

        let mut client_guard = self.client.write().await;
        let client = client_guard.as_mut()
            .ok_or(ZvecBridgeError::NotConnected)?;

        let request = Request::new(IndexRequest {
            entry: Some(MemoryEntry {
                id: entry_id.to_string(),
                content: content.to_string(),
                embedding: Some(Vector { values: embedding }),
                metadata: serde_json::to_string(metadata).unwrap_or_default(),
                timestamp: Utc::now().timestamp() as u64,
            }),
            batch: false,
        });

        let _response = client.index(request).await
            .map_err(|e| ZvecBridgeError::GrpcError(e.to_string()))?;

        let mut metrics = self.metrics.write().await;
        metrics.avg_index_latency_ms =
            (metrics.avg_index_latency_ms * metrics.total_indexed as f64 + start.elapsed().as_millis() as f64)
            / (metrics.total_indexed + 1) as f64;
        metrics.total_indexed += 1;

        info!("📥 Indexed memory entry: {} (time={}ms)", entry_id, start.elapsed().as_millis());

        Ok(())
    }

    /// ============================================================
    /// 2.4 BATCH INDEX
    /// ============================================================

    /// Indexa múltiplas entradas em batch
    pub async fn batch_index(
        &self,
        entries: Vec<(String, String, MemoryMetadata)>,
    ) -> Result<Vec<String>, ZvecBridgeError> {
        let mut indexed = vec![];

        for chunk in entries.chunks(self.config.index_batch_size) {
            let mut client_guard = self.client.write().await;
            let client = client_guard.as_mut()
                .ok_or(ZvecBridgeError::NotConnected)?;

            let zvec_entries: Vec<MemoryEntry> = futures::future::try_join_all(
                chunk.iter().map(|(id, content, meta)| async move {
                    let emb = self.generate_embedding(content).await?;
                    Ok::<MemoryEntry, ZvecBridgeError>(MemoryEntry {
                        id: id.clone(),
                        content: content.clone(),
                        embedding: Some(Vector { values: emb }),
                        metadata: serde_json::to_string(meta).unwrap_or_default(),
                        timestamp: Utc::now().timestamp() as u64,
                    })
                })
            ).await?;

            let request = Request::new(IndexRequest {
                entry: None,
                batch: true,
            });

            // Em produção: enviar batch completo
            for entry in zvec_entries {
                let single_request = Request::new(IndexRequest {
                    entry: Some(entry.clone()),
                    batch: false,
                });
                client.index(single_request).await
                    .map_err(|e| ZvecBridgeError::GrpcError(e.to_string()))?;
                indexed.push(entry.id);
            }
        }

        Ok(indexed)
    }

    /// ============================================================
    /// 2.5 HYBRID SEARCH (Dense + Sparse + RRF)
    /// ============================================================

    /// Busca híbrida: HNSW (dense) + BM25 (sparse) + RRF
    pub async fn hybrid_search(
        &self,
        query: &str,
        top_k: usize,
        dense_weight: f64,
        sparse_weight: f64,
    ) -> Result<Vec<SearchResult>, ZvecBridgeError> {
        let start = std::time::Instant::now();

        let mut client_guard = self.client.write().await;
        let client = client_guard.as_mut()
            .ok_or(ZvecBridgeError::NotConnected)?;

        let request = Request::new(SearchRequest {
            query_vector: None, // zVEC gera internamente
            top_k: top_k as u32,
            filter: None,
            use_hnsw: self.config.use_hnsw,
            use_bm25: self.config.use_bm25,
            rrf_weight: self.config.rrf_weight,
        });

        let response = client.hybrid_search(request).await
            .map_err(|e| ZvecBridgeError::GrpcError(e.to_string()))?;

        let results = response.into_inner().results.into_iter()
            .map(|r| SearchResult {
                entry_id: r.entry_id,
                score: r.score,
                content: r.content,
                metadata: r.metadata,
            })
            .collect();

        info!("🔍 Hybrid search: {} results in {}ms", results.len(), start.elapsed().as_millis());

        Ok(results)
    }

    /// ============================================================
    /// 2.6 MÉTRICAS
    /// ============================================================

    pub async fn get_metrics(&self) -> ZvecBridgeMetrics {
        self.metrics.read().await.clone()
    }

    pub async fn get_cache_stats(&self) -> CacheStats {
        let cache = self.embedding_cache.read().await;
        CacheStats {
            size: cache.len(),
            capacity: self.config.cache_size,
            hit_rate: {
                let metrics = self.metrics.read().await;
                let total = metrics.cache_hits + metrics.cache_misses;
                if total == 0 { 0.0 } else { metrics.cache_hits as f64 / total as f64 }
            },
        }
    }
}

/// ============================================================
/// 3. TIPOS AUXILIARES
/// ============================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMetadata {
    pub agent_id: String,
    pub task_id: String,
    pub memory_type: String,
    pub priority: f64,
    pub tags: Vec<String>,
    pub compression_ratio: f64,
}

#[derive(Debug, Clone)]
pub struct SearchResult {
    pub entry_id: String,
    pub score: f64,
    pub content: String,
    pub metadata: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchFilter {
    pub agent_id: Option<String>,
    pub task_id: Option<String>,
    pub memory_type: Option<String>,
    pub min_score: Option<f64>,
    pub tags: Option<Vec<String>>,
    pub created_after: Option<i64>,
    pub created_before: Option<i64>,
}

#[derive(Debug, Clone)]
pub struct CacheStats {
    pub size: usize,
    pub capacity: usize,
    pub hit_rate: f64,
}

/// ============================================================
/// 4. ERROS
/// ============================================================

#[derive(Debug, Error)]
pub enum ZvecBridgeError {
    #[error("Connection error: {0}")]
    ConnectionError(String),
    #[error("Not connected to zVEC server")]
    NotConnected,
    #[error("gRPC error: {0}")]
    GrpcError(String),
    #[error("Serialization error: {0}")]
    Serialization(String),
    #[error("Embedding generation failed: {0}")]
    EmbeddingFailed(String),
    #[error("Search failed: {0}")]
    SearchFailed(String),
    #[error("Index failed: {0}")]
    IndexFailed(String),
}

use chrono::Utc;

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_zvec_bridge_config() {
        let config = ZvecBridgeConfig::default();
        assert_eq!(config.embedding_dimensions, 384);
        assert!(config.use_hnsw);
        assert!(config.use_bm25);
    }

    #[test]
    fn test_search_result() {
        let result = SearchResult {
            entry_id: "test_1".to_string(),
            score: 0.95,
            content: "test content".to_string(),
            metadata: "{}".to_string(),
        };
        assert_eq!(result.score, 0.95);
    }

    #[test]
    fn test_memory_metadata() {
        let meta = MemoryMetadata {
            agent_id: "agent_1".to_string(),
            task_id: "task_1".to_string(),
            memory_type: "conversation".to_string(),
            priority: 0.8,
            tags: vec!["test".to_string()],
            compression_ratio: 0.5,
        };
        assert_eq!(meta.priority, 0.8);
    }
}
