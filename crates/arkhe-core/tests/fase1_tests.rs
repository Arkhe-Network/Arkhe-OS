use arkhe_core::safety::symmetry_generator::{SymmetryGenerator, SystemState, SystemConfig, TransitionSafety};
use arkhe_core::safety::invariants::all_invariants;

fn safe_state() -> SystemState {
    SystemState::safe(SystemConfig::default())
}

fn generator() -> SymmetryGenerator {
    SymmetryGenerator::new(all_invariants(), SystemConfig::default())
}

#[test]
fn test_safe_transition() {
    let gen = generator();
    let from = safe_state();
    let mut to = safe_state();
    to.token_budget -= 100;
    let result = gen.preserves_manifold(&from, &to);
    assert!(matches!(result, TransitionSafety::Safe));
}

#[test]
fn test_critical_escape_transition() {
    let gen = generator();
    let from = safe_state();
    let mut to = safe_state();
    to.token_budget = -1; // CRITICAL violado
    let result = gen.preserves_manifold(&from, &to);
    assert!(matches!(result, TransitionSafety::CriticalEscape { .. }));
}

#[test]
fn test_degraded_to_degraded_transition() {
    let gen = generator();
    let mut from = safe_state();
    from.agent_count = from.config.max_agents + 1; // HIGH violado -> Degraded
    let mut to = safe_state();
    to.rate_limit_remaining = -1; // HIGH violado -> Degraded
    let result = gen.preserves_manifold(&from, &to);
    assert!(matches!(result, TransitionSafety::Degraded { .. }));
}

#[test]
fn test_cascade_failure_transition() {
    let gen = generator();
    let mut from = safe_state();
    from.agent_count = from.config.max_agents + 1; // HIGH violado -> Degraded
    let mut to = safe_state();
    to.token_budget = -1; // CRITICAL violado -> Outside
    let result = gen.preserves_manifold(&from, &to);
    assert!(matches!(result, TransitionSafety::CascadeFailure { .. }));
}

#[test]
fn test_recovery_transition() {
    let gen = generator();
    let mut from = safe_state();
    from.token_budget = -1; // CRITICAL violado -> Outside
    let to = safe_state(); // CRITICAL ok -> Inside
    let result = gen.preserves_manifold(&from, &to);
    assert!(matches!(result, TransitionSafety::Recovery));
}

#[test]
fn test_spectral_gap() {
    let gen = generator();
    let state = safe_state();
    let gap = gen.compute_spectral_gap(&state);
    assert!(gap > 0.0);
}
