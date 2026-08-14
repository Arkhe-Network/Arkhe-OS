use alloc::string::String;
use core::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum AuthError {
    FastPathVerification,
    SlowPathVerification,
    KeyDerivation,
    PolicyViolation { reason: String },
    CounterExhausted,
    HardwareFailure,
    InvalidKey,
    KemDecapsulation,
    Deserialization,
    ReplayDetected,
}

impl fmt::Display for AuthError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuthError::FastPathVerification => write!(f, "fast-path verification failed"),
            AuthError::SlowPathVerification => write!(f, "slow-path verification failed"),
            AuthError::KeyDerivation => write!(f, "key derivation failed"),
            AuthError::PolicyViolation { reason } => write!(f, "policy violation: {}", reason),
            AuthError::CounterExhausted => write!(f, "counter exhausted"),
            AuthError::HardwareFailure => write!(f, "hardware/RNG failure"),
            AuthError::InvalidKey => write!(f, "invalid key format"),
            AuthError::KemDecapsulation => write!(f, "KEM decapsulation failed"),
            AuthError::Deserialization => write!(f, "message deserialization failed"),
            AuthError::ReplayDetected => write!(f, "replay or clock skew detected"),
        }
    }
}

#[cfg(feature = "std")]
#[cfg(feature = "std")]
impl core::error::Error for AuthError {}

pub type AuthResult<T> = Result<T, AuthError>;
