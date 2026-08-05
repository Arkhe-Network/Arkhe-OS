// ============================================================================
// Timechain (Arkhe) — Ledger Topológico Quântico
// ============================================================================

pub mod accelerate;
pub mod consensus;
pub mod mhd;
pub mod network;
pub mod observer;
pub mod retro;
pub mod shadow;
pub mod storage;
pub mod timechain;
pub mod utxo;

pub use accelerate::advance_mhd_gpu;
pub use consensus::ConsensusEngine;
pub use mhd::{EvoField, PlasmaConfig, ReconnectionDetector};
pub use network::{NetworkMessage, P2PNode, PeerInfo};
pub use observer::ObserverState;
pub use retro::{EchoSignal, RetroCausalChannel};
pub use shadow::{Shadow, ShadowHealer};
pub use storage::{ShadowSnapshot, ShadowStore};
pub use timechain::{ChernSimonsOracle, ShadowHash, TimeBlock};
pub use utxo::{Transaction, Utxo, UtxoRef};

pub const CHERN_SIMONS_KAPPA: f64 = 1.0;
pub const DEFAULT_VALIDATION_TOLERANCE: f64 = 1e-3;
