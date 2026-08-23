//! ARKHE Memristor Driver — DNA-Peroskite Ultra-Low Voltage
//!
//! Este crate fornece um driver para o memristor baseado em
//! Ag/(PEA)₂(MA)Pb₂I₇/Ag-synDNA/Pt, com suporte a operações
//! de SET, RESET, READ e multilevel, todos com tensão <0.1V.
//!
//! # Características
//!
//! - **Tensão de operação**: < 0.1 V (VSET ≈ 0.10 V, VRESET ≈ 0.08 V)
//! - **Potência**: 17 µW (CC = 100 µA), 0.01 W/cm² (CC = 1 mA)
//! - **ON/OFF ratio**: > 10⁵
//! - **Endurance**: > 10³ ciclos
//! - **Retenção**: > 4 × 10³ s
//! - **Estabilidade ambiente**: > 6 semanas
//! - **Temperatura**: até 393 K (120°C)
//!
//! # Exemplo de Uso
//!
//! ```
//! use arkhe_memristor::{Memristor, MemristorDriver};
//!
//! let mut mem = MemristorDriver::new();
//! mem.set_compliance_current(100e-6).unwrap(); // 100 µA
//! mem.set_voltage(0.09).unwrap(); // <0.1V
//!
//! match mem.set(None) {
//!     Ok(_) => println!("LRS (ON)"),
//!     Err(e) => eprintln!("SET failed: {}", e),
//! }
//!
//! match mem.read() {
//!     Ok(state) => println!("State: {:?}", state),
//!     Err(e) => eprintln!("READ failed: {}", e),
//! }
//! ```

#![cfg_attr(not(feature = "std"), no_std)]
#![warn(missing_docs)]
#![warn(rust_2018_idioms)]

pub mod memristor;
pub mod driver;
pub mod commands;
pub mod multilevel;
pub mod metrics;
pub mod integration;

pub use memristor::{Memristor, MemristorError, ResistanceState};
pub use driver::{MemristorDriver, DriverConfig};
pub use commands::{SetParams, ResetParams};
pub use multilevel::Level;
pub use metrics::{Metrics, PowerMetrics, EnduranceMetrics};
