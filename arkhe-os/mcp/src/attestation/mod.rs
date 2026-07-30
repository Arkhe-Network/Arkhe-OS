pub mod manager;

pub use manager::{AttestationManager, PolicyDescriptor};

// stubs
pub trait AttestationProvider: Send + Sync {
    fn run_authorized(&self, workload: &str, cost_cap: Option<f64>, identity: &crate::identity_attestation::IdentityAttestation) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<crate::identity_attestation::ExecutionAttestation, String>> + Send + '_>>;
}

pub trait AttestationVerifier: Send + Sync {
}

pub struct CathedralComputeProvider {}
