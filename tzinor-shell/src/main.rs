//! Tzinor Shell - Phase-aware Interactive Shell for Arkhe(L)
//!
//! A custom shell implementation for interacting with the Tzinor protocol,
//! Q-MCP quantum mesh network, and phase-coherent system operations.
//!
//! Features:
//! - Built-in phase/clock commands synchronized to Voyager-1LD
//! - Tzinor channel management
//! - Q-MCP network interaction
//! - Hilbert mesh visualization
//! - Retrocausal command execution

mod commands;
mod shell;
mod tzinor;
mod qmcp;
mod phase;
mod hilbert;

use anyhow::Result;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

fn main() -> Result<()> {
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .init();

    tracing::info!("🜏 Tzinor Shell v0.1.0 - Initializing...");
    
    let mut shell = shell::TzinorShell::new()?;
    shell.run()?;
    
    Ok(())
}
