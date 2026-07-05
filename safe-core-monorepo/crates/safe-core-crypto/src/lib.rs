// crates/safe-core-crypto/src/lib.rs
#![deny(unsafe_code)]

pub mod did;
pub mod error;
pub mod threshold;
pub mod tpm;
pub mod mtls;

pub use did::DidArkhe;
pub use error::CryptoError;
pub use threshold::{ThresholdSigner, ThresholdSession, ThresholdSignature, MockThresholdSigner};
pub use tpm::{TpmAttestationProvider, TpmQuote, MockTpmProvider};
pub use mtls::HybridTlsConfig;
