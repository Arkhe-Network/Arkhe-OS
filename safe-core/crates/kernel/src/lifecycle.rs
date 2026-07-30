// crates/kernel/src/lifecycle.rs
//! Ciclo de vida do sistema AGI

use tracing::{info, warn, error};

/// Estados do sistema.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SystemState {
    Initializing,
    Ready,
    Planning,
    Executing,
    Sealing,
    Frozen,
    ShuttingDown,
}

/// Gerenciador de ciclo de vida.
pub struct SystemLifecycle {
    state: SystemState,
}

impl SystemLifecycle {
    pub fn new() -> Self {
        Self {
            state: SystemState::Initializing,
        }
    }

    pub fn state(&self) -> SystemState {
        self.state
    }

    pub fn transition(&mut self, new_state: SystemState) -> Result<(), super::error::KernelError> {
        use SystemState::*;

        let valid = match (self.state, new_state) {
            (Initializing, Ready) => true,
            (Ready, Planning) => true,
            (Planning, Executing) => true,
            (Planning, Ready) => true, // Cancel
            (Executing, Sealing) => true,
            (Executing, Ready) => true, // Error recovery
            (Sealing, Ready) => true,
            (_, Frozen) => true, // Any -> Frozen (emergency)
            (Frozen, Ready) => true, // Thaw
            (Ready, ShuttingDown) => true,
            _ => false,
        };

        if !valid {
            return Err(super::error::KernelError::Config(
                format!("Invalid state transition: {:?} -> {:?}", self.state, new_state)
            ));
        }

        info!("State transition: {:?} -> {:?}", self.state, new_state);
        self.state = new_state;
        Ok(())
    }

    pub fn freeze(&mut self) {
        error!("EMERGENCY FREEZE activated");
        self.state = SystemState::Frozen;
    }

    pub fn is_frozen(&self) -> bool {
        self.state == SystemState::Frozen
    }
}

impl Default for SystemLifecycle {
    fn default() -> Self {
        Self::new()
    }
}
