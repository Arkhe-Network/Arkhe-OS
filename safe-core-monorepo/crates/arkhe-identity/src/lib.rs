// crates/arkhe-identity/src/lib.rs
//! Identidade de dispositivo (GDID) para o ARKHE OS.
#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod gdid;

pub use gdid::{CapabilityBitmap, CrlBundle, Gdid, GdidCertificate, GdidError, GdidShort, MerkleProof};
