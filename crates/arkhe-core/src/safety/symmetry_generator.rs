use std::collections::HashSet;

#[derive(Debug, Clone)]
pub struct SystemConfig {
    pub max_tokens: i64,
    pub max_agents: u32,
    pub min_fuel: i64,
    pub min_entropy: u32,
    pub max_sandbox_fuel: i64,
    pub max_rate_limit: i64,
    pub topological_gap_threshold: f64,
}

impl Default for SystemConfig {
    fn default() -> Self {
        Self {
            max_tokens: 10_000,
            max_agents: 10,
            min_fuel: 100,
            min_entropy: 256,
            max_sandbox_fuel: 1_000,
            max_rate_limit: 100,
            topological_gap_threshold: 0.2,
        }
    }
}

#[derive(Debug, Clone)]
pub struct SystemState {
    pub token_budget: i64,
    pub agent_count: u32,
    pub sandbox_fuel: i64,
    pub entropy_bits: u32,
    pub pii_scrubbed: bool,
    pub signature_valid: bool,
    pub rate_limit_remaining: i64,
    pub model_capability: u64,
    pub task_requirement: u64,
    pub config: SystemConfig,
}

impl SystemState {
    pub fn safe(config: SystemConfig) -> Self {
        Self {
            token_budget: config.max_tokens,
            agent_count: 0,
            sandbox_fuel: config.max_sandbox_fuel,
            entropy_bits: config.min_entropy * 2,
            pii_scrubbed: true,
            signature_valid: true,
            rate_limit_remaining: config.max_rate_limit,
            model_capability: u64::MAX,
            task_requirement: 0,
            config,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum InvariantClass {
    Critical,
    High,
    Medium,
    Low,
}

pub trait Invariant: Send + Sync {
    fn id(&self) -> &'static str;
    fn check(&self, state: &SystemState) -> bool;
    fn class(&self) -> InvariantClass;
    fn margin(&self, state: &SystemState) -> f64 {
        if self.check(state) { 1.0 } else { 0.0 }
    }
}

#[derive(Debug, Clone)]
pub enum ViolationType {
    Critical { invariant_ids: Vec<String> },
}

#[derive(Debug, Clone)]
pub enum ManifoldResult {
    Inside,
    Degraded(Vec<(InvariantClass, String)>),
    Outside { violation: ViolationType, state: SystemState },
}

#[derive(Debug, Clone)]
pub enum TransitionSafety {
    Safe,
    CriticalEscape { violation: ViolationType, state: SystemState },
    CascadeFailure { violation: ViolationType, state: SystemState },
    Degraded { violations: Vec<String>, warning: String },
    Unsafe { reason: String },
    Recovery,
}

pub struct SymmetryGenerator {
    invariants: Vec<Box<dyn Invariant>>,
    config: SystemConfig,
}

impl SymmetryGenerator {
    pub fn new(invariants: Vec<Box<dyn Invariant>>, config: SystemConfig) -> Self {
        Self { invariants, config }
    }

    pub fn invariants(&self) -> &Vec<Box<dyn Invariant>> {
        &self.invariants
    }

    pub fn compute_spectral_gap(&self, state: &SystemState) -> f64 {
        let margins: Vec<f64> = self.invariants.iter()
            .map(|inv| inv.margin(state))
            .collect();

        if margins.is_empty() {
            1.0
        } else {
            margins.into_iter().fold(1.0, f64::min)
        }
    }

    pub fn is_in_manifold(&self, state: &SystemState) -> ManifoldResult {
        let mut degraded = Vec::new();
        let mut critical_violations = Vec::new();

        for inv in &self.invariants {
            if !inv.check(state) {
                match inv.class() {
                    InvariantClass::Critical => critical_violations.push(inv.id().to_string()),
                    class => degraded.push((class, inv.id().to_string())),
                }
            }
        }

        if !critical_violations.is_empty() {
            ManifoldResult::Outside {
                violation: ViolationType::Critical { invariant_ids: critical_violations },
                state: state.clone(),
            }
        } else if !degraded.is_empty() {
            ManifoldResult::Degraded(degraded)
        } else {
            ManifoldResult::Inside
        }
    }

    pub fn preserves_manifold(&self, from: &SystemState, to: &SystemState) -> TransitionSafety {
        match (self.is_in_manifold(from), self.is_in_manifold(to)) {
            (ManifoldResult::Inside, ManifoldResult::Inside) => TransitionSafety::Safe,
            (ManifoldResult::Inside, ManifoldResult::Outside { violation, state }) => TransitionSafety::CriticalEscape { violation, state },
            (ManifoldResult::Degraded(_), ManifoldResult::Outside { violation, state }) => TransitionSafety::CascadeFailure { violation, state },
            (ManifoldResult::Inside, ManifoldResult::Degraded(v)) | (ManifoldResult::Degraded(_), ManifoldResult::Degraded(v)) => {
                TransitionSafety::Degraded {
                    violations: v.into_iter().map(|(_, id)| id).collect(),
                    warning: "System degraded".into(),
                }
            }
            (ManifoldResult::Outside { .. }, ManifoldResult::Inside) => TransitionSafety::Recovery,
            (ManifoldResult::Outside { .. }, ManifoldResult::Degraded(_)) => TransitionSafety::Unsafe { reason: "Outside to Degraded".into() },
            (ManifoldResult::Outside { .. }, ManifoldResult::Outside { .. }) => TransitionSafety::Unsafe { reason: "Outside to Outside".into() },
            (ManifoldResult::Degraded(_), ManifoldResult::Inside) => TransitionSafety::Recovery,
        }
    }
}
