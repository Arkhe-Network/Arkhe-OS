#[cfg(feature = "signing")]
use crate::keypair::ArtifactKeyPair;

/// Signatário de artefatos — wrapper em torno de ArtifactKeyPair.
pub struct ArtifactSigner {
    keypair: ArtifactKeyPair,
}

#[cfg(feature = "signing")]
impl ArtifactSigner {
    pub fn new() -> Result<Self, arkhe_core::ArkheError> {
        Ok(Self {
            keypair: ArtifactKeyPair::generate()?,
        })
    }

    pub fn keypair(&self) -> &ArtifactKeyPair {
        &self.keypair
    }
}
