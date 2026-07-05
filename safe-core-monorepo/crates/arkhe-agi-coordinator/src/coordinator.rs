// crates/arkhe-agi-coordinator/src/coordinator.rs
pub struct AgiCoordinator {
    // ... campos existentes ...
    policy_gateway: Option<arkhe_policy_gateway::PolicyGateway>,
    config: arkhe_configuration::Configuration,
}

impl AgiCoordinator {
    pub fn with_policy(
        policy_gateway: arkhe_policy_gateway::PolicyGateway,
        config: arkhe_configuration::Configuration,
    ) -> Self {
        // ...
    }
}
