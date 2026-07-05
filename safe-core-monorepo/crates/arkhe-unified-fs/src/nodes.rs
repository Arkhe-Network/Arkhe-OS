//! Nós do sistema de arquivos unificado — inodes virtuais.

use crate::path::UnifiedPath;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Tipo de nó.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum NodeType {
    File,
    Directory,
    Symlink,
}

/// Metadados de um nó — substitui `stat` com campos unificados.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NodeMeta {
    /// ID único do nó.
    pub node_id: String,

    /// Tipo.
    pub node_type: NodeType,

    /// Tamanho em bytes (0 para diretórios).
    pub size: u64,

    /// Criado.
    pub created_at: DateTime<Utc>,

    /// Modificado.
    pub modified_at: DateTime<Utc>,

    /// Acessado.
    pub accessed_at: DateTime<Utc>,

    /// Permissões estilo Unix (octal, ex: 0o644).
    pub mode: u32,

    /// DID do proprietário.
    pub owner_did: String,

    /// DIDs com acesso (ler, escrever, executar).
    pub acl: Vec<AclEntry>,

    /// Backend de origem ("memory", "ntfs", "ext4", "virtual").
    pub backend: String,

    /// Caminho nativo no backend (ex: `/mnt/c/Users/file.txt`).
    pub backend_path: Option<String>,

    /// Hash de integridade (blake3) para arquivos.
    pub integrity_hash: Option<String>,

    /// Se o nó está tombstoned (GDPR erasure).
    pub tombstoned: bool,

    /// Metadados estendidos (xattrs equivalent).
    pub extended: HashMap<String, String>,
}

/// Entrada ACL — controle de acesso baseado em DID.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AclEntry {
    /// DID do sujeito.
    pub did: String,
    /// Permissões.
    pub permissions: AclPermissions,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct AclPermissions {
    pub read: bool,
    pub write: bool,
    pub execute: bool,
}

impl AclPermissions {
    pub const NONE: Self = Self { read: false, write: false, execute: false };
    pub const READ: Self = Self { read: true, write: false, execute: false };
    pub const RW: Self = Self { read: true, write: true, execute: false };
    pub const RWX: Self = Self { read: true, write: true, execute: true };
}

/// Um nó no sistema de arquivos virtual.
#[derive(Debug, Clone)]
pub struct FsNode {
    pub meta: NodeMeta,
    /// Conteúdo do arquivo (em memória).
    /// Para backends reais, isso seria None e o conteúdo seria lido sob demanda.
    pub content: Option<Vec<u8>>,
    /// Entras do diretório (nome → node_id).
    pub children: HashMap<String, String>,
}

impl FsNode {
    /// Cria um diretório raiz.
    pub fn root(owner_did: &str) -> Self {
        Self {
            meta: NodeMeta {
                node_id: "root".into(),
                node_type: NodeType::Directory,
                size: 0,
                created_at: Utc::now(),
                modified_at: Utc::now(),
                accessed_at: Utc::now(),
                mode: 0o755,
                owner_did: owner_did.to_string(),
                acl: vec![AclEntry {
                    did: owner_did.to_string(),
                    permissions: AclPermissions::RWX,
                }],
                backend: "virtual".into(),
                backend_path: None,
                integrity_hash: None,
                tombstoned: false,
                extended: HashMap::new(),
            },
            content: None,
            children: HashMap::new(),
        }
    }

    /// Cria um arquivo.
    pub fn file(path: &UnifiedPath, owner_did: &str, content: Vec<u8>) -> Self {
        let hash = arkhe_core::blake3_hash(&content);
        Self {
            meta: NodeMeta {
                node_id: uuid::Uuid::new_v4().to_string(),
                node_type: NodeType::File,
                size: content.len() as u64,
                created_at: Utc::now(),
                modified_at: Utc::now(),
                accessed_at: Utc::now(),
                mode: 0o644,
                owner_did: owner_did.to_string(),
                acl: vec![AclEntry {
                    did: owner_did.to_string(),
                    permissions: AclPermissions::RW,
                }],
                backend: "memory".into(),
                backend_path: None,
                integrity_hash: Some(format!("{}", hash)),
                tombstoned: false,
                extended: HashMap::new(),
            },
            content: Some(content),
            children: HashMap::new(),
        }
    }

    /// Cria um diretório.
    pub fn directory(path: &UnifiedPath, owner_did: &str) -> Self {
        Self {
            meta: NodeMeta {
                node_id: uuid::Uuid::new_v4().to_string(),
                node_type: NodeType::Directory,
                size: 0,
                created_at: Utc::now(),
                modified_at: Utc::now(),
                accessed_at: Utc::now(),
                mode: 0o755,
                owner_did: owner_did.to_string(),
                acl: vec![AclEntry {
                    did: owner_did.to_string(),
                    permissions: AclPermissions::RWX,
                }],
                backend: "virtual".into(),
                backend_path: None,
                integrity_hash: None,
                tombstoned: false,
                extended: HashMap::new(),
            }
            .meta
            .clone(),
            content: None,
            children: HashMap::new(),
        }
    }

    /// Verifica se um DID tem uma permissão específica.
    pub fn has_permission(&self, did: &str, perm: fn(&AclPermissions) -> bool) -> bool {
        // Owner sempre tem todas as permissões
        if self.meta.owner_did == did {
            return true;
        }
        // Verificar ACL
        self.meta.acl.iter().any(|entry| {
            entry.did == did && perm(&entry.permissions)
        })
    }

    /// Verifica permissão de leitura.
    pub fn can_read(&self, did: &str) -> bool {
        self.has_permission(did, |p| p.read)
    }

    /// Verifica permissão de escrita.
    pub fn can_write(&self, did: &str) -> bool {
        self.has_permission(did, |p| p.write)
    }

    /// Verifica permissão de execução.
    pub fn can_execute(&self, did: &str) -> bool {
        self.has_permission(did, |p| p.execute)
    }
}

// Helper para criar DirectoryNode a partir de meta
impl FsNode {
    pub fn from_meta(meta: NodeMeta) -> Self {
        let node_type = meta.node_type;
        Self {
            meta,
            content: None,
            children: if node_type == NodeType::Directory {
                HashMap::new()
            } else {
                HashMap::new()
            },
        }
    }
}
