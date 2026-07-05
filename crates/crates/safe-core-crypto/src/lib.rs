pub mod did;
pub mod error;
pub mod threshold;

// Formal-verification harnesses are only compiled under Kani (`cargo kani`),
// so a normal `cargo build`/`cargo test` never touches them.
#[cfg(kani)]
mod verify;

pub use did::DidArkhe;
pub use error::CryptoError;
pub use threshold::{ThresholdSignature, ThresholdSigner};
