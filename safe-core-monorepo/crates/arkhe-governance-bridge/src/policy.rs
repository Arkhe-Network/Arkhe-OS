use crate::identity::PlatformSide;
use crate::mapping::IdentityMappingStore;

/// Avaliador de políticas unificadas.
///
/// Dado um DID, resolve a identidade em cada plataforma e aplica
/// a mesma política de governança, independentemente do SO.
pub struct UnifiedPolicyEvaluator {
    store: IdentityMappingStore,
}

impl UnifiedPolicyEvaluator {
    pub fn new(store: IdentityMappingStore) -> Self {
        Self { store }
    }

    /// Verifica se uma operação é permitida para um DID em uma plataforma.
    ///
    /// Em uma implementação completa, isso integraria com:
    /// - `GovernanceGuard` do arkhe-governance
    /// - Capability Tokens
    /// - WormGraph para auditoria
    pub async fn check_operation(
        &self,
        did: &str,
        platform: PlatformSide,
        operation: &str,
        resource: &str,
    ) -> Result<PolicyDecision, String> {
        // 1. Verificar se o DID tem identidade nesta plataforma
        let identity = self
            .store
            .resolve_did(did, platform)
            .await
            .map_err(|e| format!("Identity resolution failed: {}", e))?;

        if !identity.active {
            return Ok(PolicyDecision {
                allowed: false,
                reason: format!("Identity {} is inactive on {}", did, platform),
                platform: platform.to_string(),
            });
        }

        // 2. Avaliar política (placeholder — integraria com arkhe-governance)
        // Em produção, chamaria GovernanceGuard.evaluate()
        Ok(PolicyDecision {
            allowed: true,
            reason: String::new(),
            platform: platform.to_string(),
        })
    }

    /// Verifica operação em todas as plataformas onde o DID tem identidade.
    pub async fn check_operation_all_platforms(
        &self,
        did: &str,
        operation: &str,
        resource: &str,
    ) -> Vec<PlatformPolicyResult> {
        let identities = self.store.list_identities(did).await;
        let mut results = Vec::new();

        for identity in identities {
            let decision = self
                .check_operation(did, identity.side, operation, resource)
                .await;

            results.push(PlatformPolicyResult {
                platform: identity.side,
                identifier: identity.identifier,
                decision: decision.ok(),
                display_name: identity.display_name,
            });
        }

        results
    }
}

/// Decisão de política para uma plataforma.
#[derive(Debug, Clone)]
pub struct PolicyDecision {
    pub allowed: bool,
    pub reason: String,
    pub platform: String,
}

/// Resultado por plataforma.
#[derive(Debug, Clone)]
pub struct PlatformPolicyResult {
    pub platform: PlatformSide,
    pub identifier: String,
    pub decision: Option<PolicyDecision>,
    pub display_name: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::identity::PlatformIdentity;

    #[tokio::test]
    async fn active_identity_allowed() {
        let store = IdentityMappingStore::new();
        store
            .register(
                "did:arkhe:active",
                PlatformIdentity::linux_uid_gid(1000, 1000, Some("active")),
            )
            .await
            .unwrap();

        let evaluator = UnifiedPolicyEvaluator::new(store);
        let result = evaluator
            .check_operation("did:arkhe:active", PlatformSide::Linux, "read", "/file")
            .await
            .unwrap();

        assert!(result.allowed);
    }

    #[tokio::test]
    async fn unknown_did_rejected() {
        let store = IdentityMappingStore::new();
        let evaluator = UnifiedPolicyEvaluator::new(store);

        let result = evaluator
            .check_operation("did:arkhe:unknown", PlatformSide::Linux, "read", "/file")
            .await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn check_all_platforms() {
        let store = IdentityMappingStore::new();
        let did = "did:arkhe:multi";

        store
            .register(did, PlatformIdentity::windows_sid("S-1-5-21-100", None))
            .await
            .unwrap();
        store
            .register(did, PlatformIdentity::linux_uid_gid(1000, 1000, Some("multi")))
            .await
            .unwrap();

        let evaluator = UnifiedPolicyEvaluator::new(store);
        let results = evaluator
            .check_operation_all_platforms(did, "read", "/shared/file")
            .await;

        assert_eq!(results.len(), 2);
        assert!(results.iter().all(|r| r.decision.as_ref().map(|d| d.allowed).unwrap_or(false)));
    }
}
