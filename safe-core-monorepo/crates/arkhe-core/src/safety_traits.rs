use async_trait::async_trait;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SafetyVerdict {
    Allowed,
    Rejected(String),
}

#[async_trait]
pub trait SafetyVerifier: Send + Sync {
    async fn verify(&self, action: &str, context: &str) -> SafetyVerdict;
}

pub struct AlwaysAllow;

#[async_trait]
impl SafetyVerifier for AlwaysAllow {
    async fn verify(&self, _action: &str, _context: &str) -> SafetyVerdict {
        SafetyVerdict::Allowed
    }
}
