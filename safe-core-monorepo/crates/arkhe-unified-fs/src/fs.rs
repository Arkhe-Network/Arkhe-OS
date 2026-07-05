//! Sistema de arquivos unificado — orquestra backends + ACL + audit.

use crate::backend::{FsBackend, MemoryBackend};
use crate::error::{UnifiedFsError, UnifiedFsResult};
use crate::nodes::{AclPermissions, FsNode, NodeMeta, NodeType};
use crate::path::UnifiedPath;
use std::sync::Arc;
use tracing::{debug, info, warn};

/// Evento de auditoria para WormGraph.
#[derive(Debug, Clone)]
pub struct AuditEvent {
    pub action: String,
    pub subject_did: String,
    pub path: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
    pub success: bool,
    pub details: String,
}

/// Callback de auditoria.
pub type AuditCallback = Arc<dyn Fn(AuditEvent) + Send + Sync>;

/// Sistema de arquivos unificado.
pub struct UnifiedFileSystem {
    backend: Arc<dyn FsBackend>,
    audit: Option<AuditCallback>,
    default_owner: String,
}

impl UnifiedFileSystem {
    /// Cria com backend em memória.
    pub fn new_memory(owner_did: &str) -> Self {
        let backend: Arc<dyn FsBackend> = Arc::new(MemoryBackend::new());
        Self {
            backend,
            audit: None,
            default_owner: owner_did.to_string(),
        }
    }

    /// Cria com backend customizado.
    pub fn with_backend(backend: Arc<dyn FsBackend>, owner_did: &str) -> Self {
        Self {
            backend,
            audit: None,
            default_owner: owner_did.to_string(),
        }
    }

    /// Define callback de auditoria.
    pub fn with_audit(mut self, callback: AuditCallback) -> Self {
        self.audit = Some(callback);
        self
    }

    /// Inicializa o filesystem com diretório raiz.
    pub async fn init(&self) -> UnifiedFsResult<()> {
        let root_path = UnifiedPath::from_linux("/").unwrap();
        let root_node = FsNode::root(&self.default_owner);

        if !self.backend.exists(&root_path).await {
            self.backend.create_node(&root_path, root_node).await?;
            info!("Unified FS root initialized");
        }
        Ok(())
    }

    /// Registra evento de auditoria.
    fn audit(&self, action: &str, did: &str, path: &str, success: bool, details: &str) {
        if let Some(ref cb) = self.audit {
            cb(AuditEvent {
                action: action.to_string(),
                subject_did: did.to_string(),
                path: path.to_string(),
                timestamp: chrono::Utc::now(),
                success,
                details: details.to_string(),
            });
        }
    }

    /// Verifica permissão antes da operação.
    async fn check_permission(
        &self,
        path: &UnifiedPath,
        did: &str,
        action: &str,
        check: impl Fn(&FsNode) -> bool,
    ) -> UnifiedFsResult<()> {
        let meta = self.backend.get_meta(path).await.map_err(|e| {
            self.audit(action, did, &path.to_ufs(), false, &e.to_string());
            e
        })?;

        let node = FsNode::from_meta(meta);
        if !check(&node) {
            self.audit(action, did, &path.to_ufs(), false, "permission denied");
            return Err(UnifiedFsError::PermissionDenied {
                subject: did.to_string(),
                action: action.to_string(),
                path: path.to_ufs(),
                reason: "DID not in ACL and not owner".into(),
            });
        }
        Ok(())
    }

    // ── Operações de arquivo ──────────────────────────────────────

    /// Cria um arquivo.
    pub async fn create_file(
        &self,
        path: &UnifiedPath,
        did: &str,
        content: Vec<u8>,
    ) -> UnifiedFsResult<NodeMeta> {
        self.check_parent_exists(path).await?;
        let node = FsNode::file(path, did, content);
        let result = self.backend.create_node(path, node).await;
        self.audit(
            "create_file",
            did,
            &path.to_ufs(),
            result.is_ok(),
            "",
        );
        result
    }

    /// Lê um arquivo.
    pub async fn read_file(&self, path: &UnifiedPath, did: &str) -> UnifiedFsResult<Vec<u8>> {
        self.check_permission(path, did, "read", |n| n.can_read(did))
            .await?;
        let result = self.backend.read_file(path).await;
        self.audit("read_file", did, &path.to_ufs(), result.is_ok(), "");
        result
    }

    /// Escreve em um arquivo.
    pub async fn write_file(
        &self,
        path: &UnifiedPath,
        did: &str,
        content: &[u8],
    ) -> UnifiedFsResult<()> {
        self.check_permission(path, did, "write", |n| n.can_write(did))
            .await?;
        let result = self.backend.write_file(path, content).await;
        self.audit("write_file", did, &path.to_ufs(), result.is_ok(), "");
        result
    }

    /// Remove um arquivo.
    pub async fn remove_file(&self, path: &UnifiedPath, did: &str) -> UnifiedFsResult<()> {
        self.check_permission(path, did, "remove", |n| n.can_write(did))
            .await?;
        let result = self.backend.remove_node(path).await;
        self.audit("remove_file", did, &path.to_ufs(), result.is_ok(), "");
        result
    }

    // ── Operações de diretório ────────────────────────────────────

    /// Cria um diretório.
    pub async fn create_dir(
        &self,
        path: &UnifiedPath,
        did: &str,
    ) -> UnifiedFsResult<NodeMeta> {
        self.check_parent_exists(path).await?;
        let node = FsNode::directory(path, did);
        let result = self.backend.create_node(path, node).await;
        self.audit("create_dir", did, &path.to_ufs(), result.is_ok(), "");
        result
    }

    /// Lista diretório.
    pub async fn readdir(
        &self,
        path: &UnifiedPath,
        did: &str,
    ) -> UnifiedFsResult<Vec<(String, NodeMeta)>> {
        self.check_permission(path, did, "readdir", |n| n.can_read(did))
            .await?;
        self.backend.readdir(path).await
    }

    /// Remove diretório (deve estar vazio).
    pub async fn remove_dir(&self, path: &UnifiedPath, did: &str) -> UnifiedFsResult<()> {
        self.check_permission(path, did, "remove_dir", |n| n.can_write(did))
            .await?;

        // Verificar se está vazio
        let entries = self.backend.readdir(path).await?;
        if !entries.is_empty() {
            return Err(UnifiedFsError::Internal(format!(
                "Directory not empty: {} entries",
                entries.len()
            )));
        }

        let result = self.backend.remove_node(path).await;
        self.audit("remove_dir", did, &path.to_ufs(), result.is_ok(), "");
        result
    }

    // ── Metadados ─────────────────────────────────────────────────

    /// Obtém metadados.
    pub async fn stat(&self, path: &UnifiedPath, did: &str) -> UnifiedFsResult<NodeMeta> {
        self.check_permission(path, did, "stat", |n| n.can_read(did))
            .await?;
        self.backend.get_meta(path).await
    }

    /// Verifica se existe.
    pub async fn exists(&self, path: &UnifiedPath) -> bool {
        self.backend.exists(path).await
    }

    // ── ACL ───────────────────────────────────────────────────────

    /// Adiciona entrada ACL a um nó.
    pub async fn add_acl(
        &self,
        path: &UnifiedPath,
        did: &str,
        target_did: &str,
        permissions: AclPermissions,
    ) -> UnifiedFsResult<()> {
        // Verificar se o solicitante é owner
        let meta = self.backend.get_meta(path).await?;
        if meta.owner_did != did {
            return Err(UnifiedFsError::PermissionDenied {
                subject: did.to_string(),
                action: "acl_modify".into(),
                path: path.to_ufs(),
                reason: "Only owner can modify ACL".into(),
            });
        }

        // Esta operação requer acesso direto ao backend.
        // Para o MemoryBackend, faríamos mutation direta.
        // Em uma implementação completa, o backend teria um método set_acl.
        warn!(
            path = %path,
            "ACL modification requested — backend does not support live ACL update"
        );
        Ok(())
    }

    // ── Helpers ───────────────────────────────────────────────────

    async fn check_parent_exists(&self, path: &UnifiedPath) -> UnifiedFsResult<()> {
        if let Some(parent) = path.parent() {
            if !self.backend.exists(&parent).await {
                return Err(UnifiedFsError::NotFound {
                    path: parent.to_ufs(),
                });
            }
        }
        Ok(())
    }
}
