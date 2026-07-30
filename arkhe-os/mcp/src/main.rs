use std::sync::Arc;
use tracing::info;

pub mod mcp;
pub mod attestation;
pub mod identity_attestation;
pub mod voice;

use mcp::server::start_mcp_server;
use attestation::{AttestationManager, AttestationVerifier, AttestationProvider};
use identity_attestation::IdentityAttestationProvider;
use voice::VoiceCore;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();
    info!("Starting Cathedral ARKHE MCP");

    let attestation_manager = Arc::new(AttestationManager {});
    let voice_core = Arc::new(VoiceCore {});

    struct DummyIdentityProvider {}
    impl IdentityAttestationProvider for DummyIdentityProvider {
        fn attest_identity(&self, _force_refresh: bool) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<identity_attestation::IdentityAttestation, String>> + Send + '_>> {
            Box::pin(async {
                Ok(identity_attestation::IdentityAttestation {
                    confidence: 0.9,
                    identity_verified: true,
                    timestamp: chrono::Utc::now().timestamp(),
                })
            })
        }
    }
    let identity_provider = Arc::new(DummyIdentityProvider {});

    struct DummyExecutionProvider {}
    impl AttestationProvider for DummyExecutionProvider {
        fn run_authorized(&self, _workload: &str, _cost_cap: Option<f64>, _identity: &identity_attestation::IdentityAttestation) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<identity_attestation::ExecutionAttestation, String>> + Send + '_>> {
            Box::pin(async {
                Ok(identity_attestation::ExecutionAttestation {
                    id: "dummy-id".to_string(),
                    policy_compliance: true,
                    policy_attestation_id: None,
                })
            })
        }
    }

    let mcp_enabled = std::env::var("ENABLE_MCP_SERVER")
        .unwrap_or_else(|_| "true".to_string())
        .parse::<bool>()
        .unwrap_or(true);

    if mcp_enabled {
        let mcp_port = std::env::var("MCP_PORT")
            .unwrap_or_else(|_| "3032".to_string())
            .parse::<u16>()
            .unwrap_or(3032);

        let mcp_token = std::env::var("MCP_AUTH_TOKEN").ok();

        let execution_provider: Arc<dyn AttestationProvider + Send + Sync> =
            Arc::new(DummyExecutionProvider {});

        let architect_verifier: Option<Arc<dyn AttestationVerifier + Send + Sync>> = None;

        let attestation_manager_clone = attestation_manager.clone();
        let identity_provider_clone = identity_provider.clone();
        let execution_provider_clone = execution_provider.clone();
        let voice_core_clone = Some(voice_core.clone());

        tokio::spawn(async move {
            if let Err(e) = start_mcp_server(
                attestation_manager_clone,
                identity_provider_clone,
                execution_provider_clone,
                architect_verifier,
                voice_core_clone,
                mcp_port,
                mcp_token,
            )
            .await
            {
                tracing::error!("❌ MCP Server falhou: {}", e);
            }
        });

        info!("🧠 MCP Server iniciado na porta {}", mcp_port);
    }

    // keep alive
    loop {
        tokio::time::sleep(tokio::time::Duration::from_secs(60)).await;
    }
}
