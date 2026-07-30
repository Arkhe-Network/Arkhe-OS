pub mod confidence;
pub mod policy_adapter;

pub use confidence::{ConfidenceTracker, CalibrationStats};
pub use policy_adapter::{PolicySuggestion, PolicyRuleSuggestion};

pub struct MetacognitiveRegulator {
    tracker: ConfidenceTracker,
    last_calibration_error: f32,
}

impl MetacognitiveRegulator {
    pub fn new(window_size: usize) -> Self {
        Self {
            tracker: ConfidenceTracker::new(window_size),
            last_calibration_error: 0.0,
        }
    }

    pub fn record_confidence(&mut self, confidence: f32, success: bool) {
        self.tracker.record(confidence, success);
        self.last_calibration_error = self.tracker.calibration_error();
    }

    pub fn calibration_error(&self) -> f32 {
        self.last_calibration_error
    }

    pub fn suggest_policy_changes(&self) -> Vec<PolicySuggestion> {
        policy_adapter::adjust_policy(self.tracker.calibration_error(), &self.tracker)
    }
}
