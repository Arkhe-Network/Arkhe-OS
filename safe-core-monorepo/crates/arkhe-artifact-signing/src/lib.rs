#![warn(missing_docs)]
#![cfg_attr(not(feature = "signing"), allow(dead_code))]

//! Assinatura criptográfica de artefatos — ed25519-dalek v2.2.0 API.
//!
//! ✅ F1 CORRIGIDO: Usa SigningKey/VerifyingKey, não Keypair (v1.x).

pub mod types;
pub mod keypair;
pub mod signer;
pub mod verifier;

pub use types::{SignedArtifact, ArtifactSignature};
pub use keypair::ArtifactKeyPair;
pub use signer::ArtifactSigner;
pub use verifier::ArtifactVerifier;
