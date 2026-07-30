//! cognitive-core — O Cérebro AGI
//!
//! Planejamento Hierárquico com heartbit-core::DagAgent
//! Modelos de Linguagem via Candle (Rust nativo)

pub mod planner;
pub mod model;
pub mod error;

pub use planner::HierarchicalPlanner;
pub use model::{ModelRegistry, CandleBackend, EmbeddingBackend};
pub use error::CognitiveError;
