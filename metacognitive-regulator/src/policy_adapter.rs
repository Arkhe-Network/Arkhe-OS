use crate::confidence::ConfidenceTracker;

#[derive(Debug, Clone)]
pub struct PolicyRuleSuggestion {
    pub rule_id: u32,
    pub condition: String,
    pub action: String,
    pub priority: u8,
}

#[derive(Debug, Clone)]
pub enum PolicySuggestion {
    AddRule(PolicyRuleSuggestion),
    ModifyRule { rule_id: u32, new_condition: String },
    RemoveRule(u32),
    AdjustThreshold { field: String, new_value: f32 },
}

pub fn adjust_policy(calibration_error: f32, tracker: &ConfidenceTracker) -> Vec<PolicySuggestion> {
    let mut suggestions = Vec::new();
    if calibration_error > 0.3 {
        // Add a rule to prove every 5 steps
        suggestions.push(PolicySuggestion::AddRule(PolicyRuleSuggestion {
            rule_id: 99,
            condition: "step_count % 5 == 0".to_string(),
            action: "prove".to_string(),
            priority: 0,
        }));
    } else if calibration_error < 0.05 && tracker.window_len() > 20 {
        // Reduce proof frequency
        suggestions.push(PolicySuggestion::AdjustThreshold {
            field: "commitment_interval".to_string(),
            new_value: 100.0,
        });
    }
    suggestions
}
