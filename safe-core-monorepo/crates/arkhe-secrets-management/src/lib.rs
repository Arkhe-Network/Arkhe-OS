// crates/arkhe-secrets-management/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Gerenciamento de segredos com auditoria.
//!
//! Backends:
//! - **InMemory**: para testes e desenvolvimento
//! - **File**: para produção (arquivo JSON criptografado — stub, usa plaintext por enquanto)
//!
//! Toda leitura/gravação é auditada na AuditTrail.

use arkhe_audit_trail::{AuditCategory, AuditOutcome, AuditTrail, NewAuditEntry};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SecretsError {
    #[error("secret not found: {0}")]
    NotFound(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("serialization error: {0}")]
    Serialization(String),

    #[error("audit error: {0}")]
    Audit(String),

    #[error("access denied to secret '{key}' for actor '{actor}'")]
    AccessDenied { key: String, actor: String },
}

pub type SecretsResult<T> = Result<T, SecretsError>;

/// Entrada de secredo.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretEntry {
    /// Valor do segredo.
    pub value: String,
    /// Metadata.
    pub metadata: HashMap<String, serde_json::Value>,
    /// Se o segredo é sensível (não deve aparecer em logs).
    pub sensitive: bool,
}

/// Trait para backends de armazenamento de segredos.
pub trait SecretStore: Send + Sync {
    /// Obtém um segredo.
    fn get(&self, key: &str) -> SecretsResult<SecretEntry>;

    /// Define um segredo.
    fn set(&self, key: &str, entry: SecretEntry) -> SecretsResult<()>;

    /// Remove um segredo.
    fn delete(&self, key: &str) -> SecretsResult<()>;

    /// Lista todas as chaves.
    fn list_keys(&self) -> Vec<String>;
}

/// Backend em memória (para testes/dev).
pub struct InMemorySecretStore {
    store: Mutex<HashMap<String, SecretEntry>>,
}

impl InMemorySecretStore {
    pub fn new() -> Self {
        Self {
            store: Mutex::new(HashMap::new()),
        }
    }
}

impl Default for InMemorySecretStore {
    fn default() -> Self {
        Self::new()
    }
}

impl SecretStore for InMemorySecretStore {
    fn get(&self, key: &str) -> SecretsResult<SecretEntry> {
        self.store
            .lock()
            .unwrap()
            .get(key)
            .cloned()
            .ok_or_else(|| SecretsError::NotFound(key.into()))
    }

    fn set(&self, key: &str, entry: SecretEntry) -> SecretsResult<()> {
        self.store.lock().unwrap().insert(key.into(), entry);
        Ok(())
    }

    fn delete(&self, key: &str) -> SecretsResult<()> {
        let mut store = self.store.lock().unwrap();
        if store.remove(key).is_some() {
            Ok(())
        } else {
            Err(SecretsError::NotFound(key.into()))
        }
    }

    fn list_keys(&self) -> Vec<String> {
        self.store.lock().unwrap().keys().cloned().collect()
    }
}

/// Gerenciador de segredos com auditoria.
pub struct SecretsManager<S: SecretStore> {
    store: S,
    audit_trail: Mutex<AuditTrail>,
}

impl<S: SecretStore> SecretsManager<S> {
    pub fn new(store: S) -> Self {
        Self {
            store,
            audit_trail: Mutex::new(AuditTrail::new()),
        }
    }

    /// Obtém um segredo (com auditoria).
    pub fn get(&self, key: &str, actor_did: &str) -> SecretsResult<SecretEntry> {
        let entry = self.store.get(key)?;
        self.audit_access(actor_did, "get", key, true)?;
        Ok(entry)
    }

    /// Obtém um segredo sem auditoria (para uso interno do sistema).
    pub fn get_silent(&self, key: &str) -> SecretsResult<SecretEntry> {
        self.store.get(key)
    }

    /// Define um segredo (com auditoria).
    pub fn set(&self, key: &str, value: &str, actor_did: &str) -> SecretsResult<()> {
        let entry = SecretEntry {
            value: value.into(),
            metadata: HashMap::new(),
            sensitive: true,
        };
        self.store.set(key, entry)?;
        self.audit_access(actor_did, "set", key, true)?;
        Ok(())
    }

    /// Remove um segredo (com auditoria).
    pub fn delete(&self, key: &str, actor_did: &str) -> SecretsResult<()> {
        self.store.delete(key)?;
        self.audit_access(actor_did, "delete", key, true)?;
        Ok(())
    }

    /// Lista chaves.
    pub fn list_keys(&self) -> Vec<String> {
        self.store.list_keys()
    }

    /// Acesso à trilha de auditoria.
    pub fn audit_trail(&self) -> std::sync::MutexGuard<'_, AuditTrail> {
        self.audit_trail.lock().unwrap()
    }

    fn audit_access(&self, actor: &str, action: &str, key: &str, success: bool) -> SecretsResult<()> {
        let mut trail = self.audit_trail.lock().map_err(|e| SecretsError::Audit(e.to_string()))?;
        let mut details = HashMap::new();
        details.insert("action".into(), serde_json::json!(action));
        details.insert("secret_key".into(), serde_json::json!(key));
        // Nunca logar o valor do segredo
        trail.record(NewAuditEntry {
            category: AuditCategory::DataAccess,
            action: format!("secret:{}", action),
            actor_did: actor.into(),
            resource: key.into(),
            outcome: if success { AuditOutcome::Success } else { AuditOutcome::Denied },
            details,
        }).map_err(|e| SecretsError::Audit(e.to_string()))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn set_and_get() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("api_key", "sk-12345", "did:arkhe:admin").unwrap();
        let entry = mgr.get("api_key", "did:arkhe:admin").unwrap();
        assert_eq!(entry.value, "sk-12345");
    }

    #[test]
    fn get_nonexistent_fails() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        let result = mgr.get("nonexistent", "did:test");
        assert!(matches!(result, Err(SecretsError::NotFound(_))));
    }

    #[test]
    fn delete_secret() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("key", "val", "did:test").unwrap();
        mgr.delete("key", "did:test").unwrap();
        assert!(mgr.get("key", "did:test").is_err());
    }

    #[test]
    fn list_keys() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("a", "1", "did:test").unwrap();
        mgr.set("b", "2", "did:test").unwrap();
        let mut keys = mgr.list_keys();
        keys.sort();
        assert_eq!(keys, vec!["a", "b"]);
    }

    #[test]
    fn get_silent_no_audit() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("key", "val", "did:test").unwrap();
        let _ = mgr.get_silent("key").unwrap();
        // Apenas 1 entrada de auditoria (do set), não 2
        assert_eq!(mgr.audit_trail().len(), 1);
    }

    #[test]
    fn get_with_audit() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("key", "val", "did:test").unwrap();
        let _ = mgr.get("key", "did:test").unwrap();
        assert_eq!(mgr.audit_trail().len(), 2);
    }

    #[test]
    fn audit_entry_does_not_contain_value() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("secret_key", "super_secret_value", "did:test").unwrap();
        let entry = &mgr.audit_trail().entries()[0];
        assert!(!entry.details.contains_key("value"));
        assert_eq!(entry.details["secret_key"], serde_json::json!("secret_key"));
    }

    #[test]
    fn delete_nonexistent_fails() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        assert!(mgr.delete("nonexistent", "did:test").is_err());
    }

    #[test]
    fn overwrite_secret() {
        let mgr = SecretsManager::new(InMemorySecretStore::new());
        mgr.set("key", "v1", "did:test").unwrap();
        mgr.set("key", "v2", "did:test").unwrap();
        assert_eq!(mgr.get("key", "did:test").unwrap().value, "v2");
    }
}
