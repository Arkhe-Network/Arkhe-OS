#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Governance Bridge — mapeamento de identidade cross-platform.
//!
//! Resolve o problema assimétrico de identidade:
//! - Windows usa SID (S-1-5-21-...) + Active Directory
//! - Linux usa UID/GID + PAM
//! - Arkhe usa DID (W3C) + Capability Tokens
//!
//! Este crate fornece o mapeamento bidirecional e avaliação
//! de políticas unificadas.

mod identity;
mod mapping;
mod policy;
mod error;

pub use error::{GovBridgeError, GovBridgeResult};
pub use identity::{PlatformIdentity, PlatformSide};
pub use mapping::IdentityMappingStore;
pub use policy::UnifiedPolicyEvaluator;
