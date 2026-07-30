pub struct IdentityGateway;
impl IdentityGateway {
    pub fn new() -> Self {
        Self
    }
    pub async fn verify(
        &self,
        _did: &str,
        _signature: &[u8],
        _prompt: &[u8],
    ) -> Result<bool, String> {
        Ok(true)
    }
}

pub struct SignatureGuard;
impl SignatureGuard {
    pub fn new() -> Self {
        Self
    }
    pub fn sign(&self, _message: &[u8]) -> Vec<u8> {
        vec![0; 64]
    }
    pub fn attest_object(&self, obj: &mut cathedral_arkheobex::ArkheObject) -> Result<(), String> {
        obj.add_header(cathedral_arkheobex::HeaderType::PqcAttestation, vec![0xF8]);
        Ok(())
    }
}
