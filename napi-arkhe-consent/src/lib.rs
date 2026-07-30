use metacognitive_regulator::PolicySuggestion;
use cathedral_embodied_no_std::embodied_cognitive_core::EmbodiedCognitiveCore;

// Mock global core access
fn get_global_core() -> Result<EmbodiedCognitiveCore, String> {
    Ok(EmbodiedCognitiveCore::new(false))
}

pub struct PolicySuggestionJs {}
impl From<PolicySuggestion> for PolicySuggestionJs {
    fn from(_: PolicySuggestion) -> Self { Self {} }
}

// #[napi]
pub fn query_symbolic_plan(query: String) -> Result<String, String> {
    let core = get_global_core()?;
    core.query_symbolic_plan(&query).ok_or_else(|| "Plan not found".to_string())
}

// #[napi]
pub fn get_policy_suggestions() -> Result<Vec<PolicySuggestionJs>, String> {
    let core = get_global_core()?;
    let suggestions = core.meta_regulator.suggest_policy_changes();
    Ok(suggestions.into_iter().map(|s| s.into()).collect())
}

pub struct Buffer {}
// #[napi]
pub async fn submit_evidence(_proof_hash: Buffer, _action_json: String) -> Result<bool, String> {
    let _core = get_global_core()?;
    Ok(true)
}
