use crate::error::{GovBridgeError, GovBridgeResult};
use crate::identity::{PlatformIdentity, PlatformSide};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Armazena mapeamentos entre identidades de diferentes plataformas.
///
/// Estrutura: `DID` é a chave primária (fonte de verdade).
/// Cada DID pode ter múltiplas identidades platform-specific.
pub struct IdentityMappingStore {
    /// `DID → { side → PlatformIdentity }`
    mappings: RwLock<HashMap<String, HashMap<PlatformSide, PlatformIdentity>>>,
    /// Índice reverso: `side:identifier → DID`
    reverse: RwLock<HashMap<(PlatformSide, String), String>>,
}

impl IdentityMappingStore {
    pub fn new() -> Self {
        Self {
            mappings: RwLock::new(HashMap::new()),
            reverse: RwLock::new(HashMap::new()),
        }
    }

    /// Registra um mapeamento DID ↔ identidade platform.
    pub async fn register(&self, did: &str, identity: PlatformIdentity) -> GovBridgeResult<()> {
        let side = identity.side;
        let identifier = identity.identifier.clone();

        // Verificar conflito no índice reverso
        let reverse = self.reverse.read().await;
        if let Some(existing_did) = reverse.get(&(side, identifier.clone())) {
            if existing_did != did {
                return Err(GovBridgeError::MappingConflict {
                    did: did.to_string(),
                    existing: format!("{}:{}", side, identifier),
                });
            }
        }
        drop(reverse);

        // Inserir
        let mut mappings = self.mappings.write().await;
        let mut reverse = self.reverse.write().await;

        mappings
            .entry(did.to_string())
            .or_default()
            .insert(side, identity);
        reverse.insert((side, identifier), did.to_string());

        Ok(())
    }

    /// Resolve DID → identidade em uma plataforma específica.
    pub async fn resolve_did(
        &self,
        did: &str,
        side: PlatformSide,
    ) -> GovBridgeResult<PlatformIdentity> {
        let mappings = self.mappings.read().await;
        mappings
            .get(did)
            .and_then(|m| m.get(&side))
            .cloned()
            .ok_or_else(|| GovBridgeError::IdentityNotFound {
                side: side.to_string(),
                identifier: did.to_string(),
            })
    }

    /// Resolve identidade platform → DID (reverso).
    pub async fn resolve_identity(
        &self,
        side: PlatformSide,
        identifier: &str,
    ) -> GovBridgeResult<String> {
        let reverse = self.reverse.read().await;
        reverse
            .get(&(side, identifier.to_string()))
            .cloned()
            .ok_or_else(|| GovBridgeError::IdentityNotFound {
                side: side.to_string(),
                identifier: identifier.to_string(),
            })
    }

    /// Lista todas as identidades de um DID.
    pub async fn list_identities(&self, did: &str) -> Vec<PlatformIdentity> {
        let mappings = self.mappings.read().await;
        mappings
            .get(did)
            .map(|m| m.values().cloned().collect())
            .unwrap_or_default()
    }

    /// Remove mapeamento para uma plataforma específica.
    pub async fn unregister(&self, did: &str, side: PlatformSide) -> GovBridgeResult<()> {
        let mut mappings = self.mappings.write().await;
        let mut reverse = self.reverse.write().await;

        if let Some(identities) = mappings.get_mut(did) {
            if let Some(removed) = identities.remove(&side) {
                reverse.remove(&(side, removed.identifier));
            }
        }

        Ok(())
    }

    /// Retorna o número total de DIDs registrados.
    pub async fn did_count(&self) -> usize {
        self.mappings.read().await.len()
    }
}

impl Default for IdentityMappingStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn register_and_resolve() {
        let store = IdentityMappingStore::new();
        let did = "did:arkhe:test-user";

        store
            .register(
                did,
                PlatformIdentity::windows_sid(
                    "S-1-5-21-1001",
                    Some("Test User"),
                ),
            )
            .await
            .unwrap();

        store
            .register(
                did,
                PlatformIdentity::linux_uid_gid(1000, 1000, Some("testuser")),
            )
            .await
            .unwrap();

        // DID → Windows
        let win = store.resolve_did(did, PlatformSide::Windows).await.unwrap();
        assert_eq!(win.identifier, "S-1-5-21-1001");

        // DID → Linux
        let linux = store.resolve_did(did, PlatformSide::Linux).await.unwrap();
        assert_eq!(linux.linux_uid(), Some(1000));

        // Reverse: Windows → DID
        let resolved_did = store
            .resolve_identity(PlatformSide::Windows, "S-1-5-21-1001")
            .await
            .unwrap();
        assert_eq!(resolved_did, did);

        // Reverse: Linux → DID
        let resolved_did2 = store
            .resolve_identity(PlatformSide::Linux, "uid:1000:gid:1000")
            .await
            .unwrap();
        assert_eq!(resolved_did2, did);
    }

    #[tokio::test]
    async fn conflict_detection() {
        let store = IdentityMappingStore::new();

        store
            .register(
                "did:arkhe:user-a",
                PlatformIdentity::windows_sid("S-1-5-21-1001", None),
            )
            .await
            .unwrap();

        // Mesmo SID para DID diferente → conflito
        let result = store
            .register(
                "did:arkhe:user-b",
                PlatformIdentity::windows_sid("S-1-5-21-1001", None),
            )
            .await;

        assert!(matches!(result, Err(GovBridgeError::MappingConflict { .. })));
    }

    #[tokio::test]
    async fn same_did_same_identity_is_ok() {
        let store = IdentityMappingStore::new();

        store
            .register(
                "did:arkhe:user-a",
                PlatformIdentity::linux_uid_gid(1000, 1000, None),
            )
            .await
            .unwrap();

        // Re-registrar o mesmo DID com a mesma identidade → OK (idempotente)
        let result = store
            .register(
                "did:arkhe:user-a",
                PlatformIdentity::linux_uid_gid(1000, 1000, None),
            )
            .await;

        assert!(result.is_ok());
    }

    #[tokio::test]
    async fn resolve_unknown_returns_error() {
        let store = IdentityMappingStore::new();

        let result = store
            .resolve_did("did:arkhe:nobody", PlatformSide::Windows)
            .await;

        assert!(matches!(result, Err(GovBridgeError::IdentityNotFound { .. })));
    }

    #[tokio::test]
    async fn unregister() {
        let store = IdentityMappingStore::new();
        let did = "did:arkhe:temp";

        store
            .register(did, PlatformIdentity::linux_uid_gid(2000, 2000, None))
            .await
            .unwrap();

        store.unregister(did, PlatformSide::Linux).await.unwrap();

        let result = store.resolve_did(did, PlatformSide::Linux).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn list_all_identities() {
        let store = IdentityMappingStore::new();
        let did = "did:arkhe:multi";

        store
            .register(did, PlatformIdentity::arkhe_did(did, Some("Multi")))
            .await
            .unwrap();
        store
            .register(did, PlatformIdentity::windows_sid("S-1-5-21-999", None))
            .await
            .unwrap();
        store
            .register(did, PlatformIdentity::linux_uid_gid(3000, 3000, None))
            .await
            .unwrap();

        let identities = store.list_identities(did).await;
        assert_eq!(identities.len(), 3);
    }

    #[tokio::test]
    async fn did_count() {
        let store = IdentityMappingStore::new();
        assert_eq!(store.did_count().await, 0);

        store
            .register("did:arkhe:a", PlatformIdentity::linux_uid_gid(1, 1, None))
            .await
            .unwrap();
        store
            .register("did:arkhe:b", PlatformIdentity::linux_uid_gid(2, 2, None))
            .await
            .unwrap();

        assert_eq!(store.did_count().await, 2);
    }
}
