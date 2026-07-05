// ============================================================================
// ARKHE Ω-TEMP KERNEL — Library surface (no_std + alloc)
// ============================================================================
// A lógica do kernel é exposta como biblioteca `no_std` para poder ser
// compilada e verificada tanto para um alvo hospedado (`cargo check`) quanto
// para um alvo bare-metal. O ponto de entrada bare-metal fica em `main.rs`
// atrás de um gate `target_os = "none"`.
// ============================================================================

#![cfg_attr(not(test), no_std)]

extern crate alloc;

pub mod temporal_chain;
pub mod model_loader;
pub mod inference_loop;
pub mod qip_engine;
pub mod qart_engine;
pub mod orbital_mesh;
pub mod watchdog;
