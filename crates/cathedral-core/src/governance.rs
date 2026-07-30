#[derive(Debug, Clone)]
pub struct PolicyDescriptor {
    pub name: String,
}

pub struct GeometricPolicyEngine {}

impl GeometricPolicyEngine {
    pub fn new() -> Self {
        Self {}
    }

    pub async fn list_active_policies(&self) -> Result<Vec<PolicyDescriptor>, String> {
        Ok(vec![])
    }
}
