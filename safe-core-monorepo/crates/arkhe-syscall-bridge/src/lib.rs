#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Syscall Bridge — registro de mapeamento Windows↔Linux.
//!
//! Este crate **não executa** syscalls — ele fornece a infraestrutura de
//! mapeamento que um runtime (usando Syscall User Dispatch no Linux ou
//! um shim no Windows) usaria para redirecionar chamadas.
//!
//! A execução real requer:
//! - Linux: `prctl(PR_SET_SYSCALL_USER_DISPATCH, ...)` + seccomp
//! - Windows: Um hooking mechanism (detours, ou equivalente)
//!
//! Este crate foca na **tabela de mapeamento** e nas **regras de permissão**.

mod mapping;
mod registry;
mod error;

pub use error::{BridgeError, BridgeResult};
pub use mapping::{SyscallCategory, SyscallMapping, SyscallSide};
pub use registry::SyscallRegistry;
