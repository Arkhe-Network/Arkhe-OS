//! Trait de backend de armazenamento.
//!
//! O UFS pode usar múltiplos backends simultaneamente:
//! - `MemoryBackend`: em memória (testes, virtual)
//! - `NativeBackend`: acessa o filesystem real do SO hospedeiro
//! - `NtfsBackend`: acessa NTFS via driver kernel 7.1 (futuro)
//! - `Ext4Backend`: acessa ext4 nativamente (futuro)

use crate::error::{UnifiedFsError, UnifiedFsResult};
use crate::nodes::{FsNode, NodeMeta, NodeType};
use crate::path::UnifiedPath;
use async_trait::async_trait;
use std::collections::HashMap;

/// Trait para backends de armazenamento do filesystem unificado.
#[async_trait]
pub trait FsBackend: Send + Sync {
    /// Nome do backend (ex: "memory", "native", "ntfs").
    fn backend_name(&self) -> &str;

    /// Cria um nó (arquivo ou diretório).
    async fn create_node(&self, path: &UnifiedPath, node: FsNode) -> UnifiedFsResult<NodeMeta>;

    /// Lê metadados de um nó.
    async fn get_meta(&self, path: &UnifiedPath) -> UnifiedFsResult<NodeMeta>;

    /// Lê conteúdo de um arquivo.
    async fn read_file(&self, path: &UnifiedPath) -> UnifiedFsResult<Vec<u8>>;

    /// Escreve conteúdo em um arquivo.
    async fn write_file(&self, path: &UnifiedPath, content: &[u8]) -> UnifiedFsResult<()>;

    /// Remove um nó.
    async fn remove_node(&self, path: &UnifiedPath) -> UnifiedFsResult<()>;

    /// Lista entras de um diretório.
    async fn readdir(&self, path: &UnifiedPath) -> UnifiedFsResult<Vec<(String, NodeMeta)>>;

    /// Renomeia/move um nó.
    async fn rename(&self, from: &UnifiedPath, to: &UnifiedPath) -> UnifiedFsResult<()>;

    /// Verifica se um nó existe.
    async fn exists(&self, path: &UnifiedPath) -> bool;
}

/// Backend em memória — para testes e filesystem virtual.
pub struct MemoryBackend {
    nodes: tokio::sync::RwLock<HashMap<String, FsNode>>,
}

impl MemoryBackend {
    pub fn new() -> Self {
        Self {
            nodes: tokio::sync::RwLock::new(HashMap::new()),
        }
    }

    fn path_key(path: &UnifiedPath) -> String {
        path.to_ufs()
    }
}

#[async_trait]
impl FsBackend for MemoryBackend {
    fn backend_name(&self) -> &str {
        "memory"
    }

    async fn create_node(&self, path: &UnifiedPath, node: FsNode) -> UnifiedFsResult<NodeMeta> {
        let key = Self::path_key(path);
        let mut nodes = self.nodes.write().await;

        if nodes.contains_key(&key) {
            return Err(UnifiedFsError::AlreadyExists { path: path.to_ufs() });
        }

        // Garantir que o diretório pai existe
        if let Some(parent) = path.parent() {
            let parent_key = Self::path_key(&parent);
            if !nodes.contains_key(&parent_key) {
                return Err(UnifiedFsError::NotFound { path: parent.to_ufs() });
            }
            // Adicionar entrada no pai
            if let Some(parent_node) = nodes.get_mut(&parent_key) {
                if let Some(name) = path.file_name() {
                    parent_node.children.insert(name.to_string(), key.clone());
                }
            }
        }

        let meta = node.meta.clone();
        nodes.insert(key, node);
        Ok(meta)
    }

    async fn get_meta(&self, path: &UnifiedPath) -> UnifiedFsResult<NodeMeta> {
        let key = Self::path_key(path);
        let nodes = self.nodes.read().await;
        nodes
            .get(&key)
            .map(|n| n.meta.clone())
            .ok_or_else(|| UnifiedFsError::NotFound { path: path.to_ufs() })
    }

    async fn read_file(&self, path: &UnifiedPath) -> UnifiedFsResult<Vec<u8>> {
        let key = Self::path_key(path);
        let nodes = self.nodes.read().await;
        let node = nodes
            .get(&key)
            .ok_or_else(|| UnifiedFsError::NotFound { path: path.to_ufs() })?;

        if node.meta.node_type != NodeType::File {
            return Err(UnifiedFsError::IsADirectory { path: path.to_ufs() });
        }

        node.content
            .clone()
            .ok_or_else(|| UnifiedFsError::Internal("File content not loaded".into()))
    }

    async fn write_file(&self, path: &UnifiedPath, content: &[u8]) -> UnifiedFsResult<()> {
        let key = Self::path_key(path);
        let mut nodes = self.nodes.write().await;

        let node = nodes
            .get_mut(&key)
            .ok_or_else(|| UnifiedFsError::NotFound { path: path.to_ufs() })?;

        if node.meta.node_type != NodeType::File {
            return Err(UnifiedFsError::IsADirectory { path: path.to_ufs() });
        }

        let hash = arkhe_core::blake3_hash(content);
        node.content = Some(content.to_vec());
        node.meta.size = content.len() as u64;
        node.meta.modified_at = chrono::Utc::now();
        node.meta.integrity_hash = Some(format!("{}", hash));
        Ok(())
    }

    async fn remove_node(&self, path: &UnifiedPath) -> UnifiedFsResult<()> {
        let key = Self::path_key(path);
        let mut nodes = self.nodes.write().await;

        // Remover entrada do pai
        if let Some(parent) = path.parent() {
            let parent_key = Self::path_key(&parent);
            if let Some(parent_node) = nodes.get_mut(&parent_key) {
                if let Some(name) = path.file_name() {
                    parent_node.children.remove(name);
                }
            }
        }

        nodes
            .remove(&key)
            .map(|_| ())
            .ok_or_else(|| UnifiedFsError::NotFound { path: path.to_ufs() })
    }

    async fn readdir(&self, path: &UnifiedPath) -> UnifiedFsResult<Vec<(String, NodeMeta)>> {
        let key = Self::path_key(path);
        let nodes = self.nodes.read().await;
        let node = nodes
            .get(&key)
            .ok_or_else(|| UnifiedFsError::NotFound { path: path.to_ufs() })?;

        if node.meta.node_type != NodeType::Directory {
            return Err(UnifiedFsError::NotADirectory { path: path.to_ufs() });
        }

        let mut entries = Vec::new();
        for (name, child_key) in &node.children {
            if let Some(child) = nodes.get(child_key) {
                entries.push((name.clone(), child.meta.clone()));
            }
        }
        entries.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(entries)
    }

    async fn rename(&self, from: &UnifiedPath, to: &UnifiedPath) -> UnifiedFsResult<()> {
        let from_key = Self::path_key(from);
        let to_key = Self::path_key(to);
        let mut nodes = self.nodes.write().await;

        let mut node = nodes
            .remove(&from_key)
            .ok_or_else(|| UnifiedFsError::NotFound { path: from.to_ufs() })?;

        // Atualizar entrada no pai de origem
        if let Some(parent) = from.parent() {
            let parent_key = Self::path_key(&parent);
            if let Some(parent_node) = nodes.get_mut(&parent_key) {
                if let Some(name) = from.file_name() {
                    parent_node.children.remove(name);
                }
            }
        }

        // Adicionar entrada no pai de destino
        if let Some(parent) = to.parent() {
            let parent_key = Self::path_key(&parent);
            if let Some(parent_node) = nodes.get_mut(&parent_key) {
                if let Some(name) = to.file_name() {
                    parent_node.children.insert(name.to_string(), to_key.clone());
                }
            }
        }

        nodes.insert(to_key, node);
        Ok(())
    }

    async fn exists(&self, path: &UnifiedPath) -> bool {
        let key = Self::path_key(path);
        self.nodes.read().await.contains_key(&key)
    }
}

impl Default for MemoryBackend {
    fn default() -> Self {
        Self::new()
    }
}
