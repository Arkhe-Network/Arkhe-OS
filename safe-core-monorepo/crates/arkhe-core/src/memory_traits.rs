//! Traits de memória para integração com arkhe-agi.
//!
//! arkhe-agi usa estas traits em vez de depender de arkhe-memory diretamente.

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Entrada de memória genérica.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub key: String,
    pub value: String,
    pub score: f32,
    pub layer: MemoryLayer,
    pub timestamp: DateTime<Utc>,
}

/// Camada de memória.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum MemoryLayer {
    Working,
    Episodic,
    Semantic,
    Procedural,
}

/// Trait para memória do agente.
///
/// Implementado por `EvolutionaryMemory` do arkhe-memory,
/// mas arkhe-agi só conhece esta interface.
#[async_trait]
pub trait AgentMemory: Send + Sync {
    /// Armazena uma entrada na memória.
    async fn store(&self, entry: MemoryEntry) -> Result<(), String>;

    /// Recupera entradas por chave (exata).
    async fn get(&self, key: &str) -> Option<MemoryEntry>;

    /// Busca entradas por relevância.
    async fn search(&self, query: &str, limit: usize) -> Vec<MemoryEntry>;
}

/// Memória em memória — útil para testes e desenvolvimento.
#[derive(Default)]
pub struct InMemoryAgentMemory {
    store: tokio::sync::RwLock<std::collections::HashMap<String, MemoryEntry>>,
}

impl InMemoryAgentMemory {
    pub fn new() -> Self {
        Self::default()
    }
}

#[async_trait]
impl AgentMemory for InMemoryAgentMemory {
    async fn store(&self, entry: MemoryEntry) -> Result<(), String> {
        let mut store = self.store.write().await;
        store.insert(entry.key.clone(), entry);
        Ok(())
    }

    async fn get(&self, key: &str) -> Option<MemoryEntry> {
        let store = self.store.read().await;
        store.get(key).cloned()
    }

    async fn search(&self, query: &str, limit: usize) -> Vec<MemoryEntry> {
        let store = self.store.read().await;
        let query_lower = query.to_lowercase();
        let mut results: Vec<&MemoryEntry> = store
            .values()
            .filter(|e| e.value.to_lowercase().contains(&query_lower))
            .take(limit)
            .collect();
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        results.into_iter().cloned().collect()
    }
}
