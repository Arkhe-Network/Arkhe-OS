//! Arkhe Cloud Provider — Abstração genérica para provedores de nuvem federados.
//! Alinhado com IEEE 2302 (SIIF) e ISO/IEC 5140:2024.

#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod traits;
pub mod types;

#[cfg(feature = "opennebula")]
pub mod opennebula;
#[cfg(feature = "opennebula")]
pub use opennebula::OpenNebulaProvider;

#[cfg(feature = "openstack")]
pub mod openstack;
#[cfg(feature = "openstack")]
pub use openstack::OpenStackProvider;

pub use traits::{CloudProvider, InstanceAction};
pub use types::*;
