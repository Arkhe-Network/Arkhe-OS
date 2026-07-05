//! Traits de verificação de segurança.
//!
//! arkhe-agi usa estas traits em vez de depender de arkhe-pea diretamente.

use async_trait::async_trait;

/// Resultado de uma verificação de segurança.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SafetyVerdict {
    /// Ação permitida.
    Allowed,
    /// Ação rejeitada com motivo.
    Rejected(String),
}

/// Trait para verificação de segurança de intenções.
///
/// Implementado por `SafetyEnforcer` do arkhe-pea,
/// mas arkhe-agi só conhece esta interface.
#[async_trait]
pub trait SafetyVerifier: Send + Sync {
    /// Verifica se uma ação é segura.
    async fn verify(&self, action: &str, context: &str) -> SafetyVerdict;
}

/// Verificador que sempre aprova — útil para testes e modo dev.
pub struct AlwaysAllowVerifier;

#[async_trait]
impl SafetyVerifier for AlwaysAllowVerifier {
    async fn verify(&self, _action: &str, _context: &str) -> SafetyVerdict {
        SafetyVerdict::Allowed
    }
}

/// Verificador que sempre rejeita — útil para testes.
pub struct AlwaysRejectVerifier {
    pub reason: String,
}

#[async_trait]
impl SafetyVerifier for AlwaysRejectVerifier {
    async fn verify(&self, _action: &str, _context: &str) -> SafetyVerdict {
        SafetyVerdict::Rejected(self.reason.clone())
    }
}
