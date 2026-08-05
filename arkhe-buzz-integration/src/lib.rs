//! # Arkhe + Buzz Integration v0.1.0
//!
//! Integration of Arkhe's S-Measure, safety barrier, and reentry loop
//! with Block's Buzz Nostr-based collaboration platform.
//!
//! ## Verified Research
//! - **Buzz** (Block, July 2026): Real open-source platform. Apache 2.0.
//!   26 Rust crates, ~300K LOC, Nostr protocol, secp256k1 identity.
//! - **SandboxEscapeBench** (Oxford/UK AISI, March 2026): Real benchmark.
//!   18 CTF scenarios across orchestration, runtime, kernel layers.
//! - **S-Measure** (Titov 2026): Project formalism. O(N³) via nalgebra.
//!
//! ## Architecture
//! ```text
//! ┌─────────────────────────────────────────────────────────────┐
//! │                    BUZZ WORKSPACE                          │
//! │              (Nostr Relays + Rust + Buzz)                  │
//! ├─────────────────────────────────────────────────────────────┤
//! │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
//! │  │  Agent A    │  │  Agent B    │  │  Agent C    │       │
//! │  │  S=0.73     │  │  S=0.91     │  │  S=0.42     │       │
//! │  │  ρ=1.2      │  │  ρ=1.5      │  │  ρ=1.0      │       │
//! │  │  kind:39000 │  │  kind:39000 │  │  kind:39000 │       │
//! │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
//! │         │                │                │              │
//! │         └────────────────┼────────────────┘              │
//! │                          │                               │
//! │              ┌───────────▼───────────┐                   │
//! │              │   NOSTR RELAYS        │                   │
//! │              │   (signed events)     │                   │
//! │              └───────────┬───────────┘                   │
//! │                          │                               │
//! │              ┌───────────▼───────────┐                   │
//! │              │   ORCHESTRATOR        │                   │
//! │              │   (kind:39003 tasks)  │                   │
//! │              └───────────────────────┘                   │
//! └─────────────────────────────────────────────────────────────┘
//! ```
//!
//! ## Quick Start
//! ```rust,no_run
//! use arkhe_buzz_integration::{ArkheBuzzAgent, SafetyBarrier, BuzzOrchestrator};
//!
//! // Create agent with 8-dimensional D↔I loop, ρ=1.2, complexity n=5
//! let mut agent = ArkheBuzzAgent::new(8, 1.2, 5.0, 1.0);
//!
//! // Execute reentry step with external input
//! agent.reentry_step(&[0.1, 0.2, 0.1, 0.0, 0.1, 0.2, 0.1, 0.0]).unwrap();
//!
//! // Check escape risk
//! let risk = agent.check_escape();
//!
//! // Execute action safely
//! SafetyBarrier::safe_execute(&mut agent, |a| {
//!     a.d_subsystem = a.d_subsystem.map(|x| x + 0.05);
//! }, "increase_drive").unwrap();
//!
//! // Build Nostr heartbeat event
//! let event = agent.build_heartbeat_event().unwrap();
//! ```

pub mod error;
pub mod events;
pub mod s_measure;
pub mod agent;
pub mod particle;
pub mod ledger;
pub mod safety;
pub mod orchestrator;

// Re-exports
pub use error::{ArkheBuzzError, Result};
pub use events::{
    ArkheKind, SMeasureContent, SafetyAlertContent, StateSnapshotContent,
    TaskDelegationContent, EscapeRiskContent, build_arkhe_event,
};
pub use s_measure::{
    s_measure_formal, s_measure_approximate, belief_curvature,
    reentry_coherence, surrender_fraction, mermin_ratio,
    DSubsystem, ISubsystem, ReentryOperator,
};
pub use agent::{ArkheBuzzAgent, AgentSnapshot, EscapeRisk};
pub use safety::SafetyBarrier;
pub use orchestrator::{
    BuzzOrchestrator, DiscoveredAgent, TaskRequest,
    ConsensusVote, ConsensusResult, OrchestratorStats,
};
