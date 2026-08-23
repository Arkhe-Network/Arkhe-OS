//! Inference activation policies triggered by phonon precursors.
//!
//! When a precursor is detected, the edge sensor must decide how to
//! allocate its limited resources (CPU, battery, radio bandwidth).
//! This module implements activation policies that map precursor
//! events to concrete inference actions.

use crate::phonon::precursor::{PrecursorAction, PrecursorEvent};
use serde::{Deserialize, Serialize};
use tracing::{debug, info, warn};

/// Policy for activating inference based on precursor events.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ActivationPolicy {
    /// Never pre-activate; only run inference on fixed schedule
    Passive,
    /// Pre-activate only when precursor strength exceeds threshold
    Threshold { min_strength: f64 },
    /// Pre-activate with strength-proportional sampling rate increase
    Proportional { max_oversampling: f64 },
    /// Always pre-activate when any precursor is detected
    Aggressive,
    /// Custom policy with hysteresis to avoid oscillation
    Hysteresis {
        activate_threshold: f64,
        deactivate_threshold: f64,
    },
}

impl Default for ActivationPolicy {
    fn default() -> Self {
        ActivationPolicy::Hysteresis {
            activate_threshold: 1.5,
            deactivate_threshold: 0.5,
        }
    }
}

/// State of the inference engine.
#[derive(Debug, Clone, PartialEq)]
pub enum InferenceState {
    /// Inference engine is idle / powered down
    Idle,
    /// Inference engine is warming up (model loading, cache prep)
    WarmingUp,
    /// Inference engine is active and processing
    Active,
    /// Inference engine is in high-alert mode (max sampling, max model)
    HighAlert,
}

/// Activator that manages inference state based on precursor events.
pub struct InferenceActivator {
    policy: ActivationPolicy,
    state: InferenceState,
    /// Current sampling rate multiplier (1.0 = baseline)
    sampling_multiplier: f64,
    /// Baseline sampling rate in Hz
    baseline_sampling_hz: f64,
    /// Number of consecutive windows in current state
    state_duration: usize,
    /// Maximum duration in HighAlert before forced cooldown
    max_high_alert_duration: usize,
}

impl InferenceActivator {
    /// Creates a new activator with the given policy.
    pub fn new(
        policy: ActivationPolicy,
        baseline_sampling_hz: f64,
        max_high_alert_duration: usize,
    ) -> Self {
        Self {
            policy,
            state: InferenceState::Idle,
            sampling_multiplier: 1.0,
            baseline_sampling_hz,
            state_duration: 0,
            max_high_alert_duration,
        }
    }

    /// Processes a precursor event and updates inference state.
    ///
    /// Returns the recommended action for this cycle.
    pub fn process_event(&mut self, event: &PrecursorEvent) -> ActivationDecision {
        let strength = event.signature.strength_score();

        debug!(
            "Processing precursor event: strength={:.2}, action={:?}, state={:?}",
            strength, event.recommended_action, self.state
        );

        let decision = match &self.policy {
            ActivationPolicy::Passive => {
                self.state = InferenceState::Idle;
                self.sampling_multiplier = 1.0;
                ActivationDecision::Maintain
            }

            ActivationPolicy::Threshold { min_strength } => {
                if strength >= *min_strength {
                    self.transition_to(InferenceState::Active);
                    self.sampling_multiplier = 2.0;
                    ActivationDecision::Activate
                } else {
                    self.transition_to(InferenceState::Idle);
                    self.sampling_multiplier = 1.0;
                    ActivationDecision::Maintain
                }
            }

            ActivationPolicy::Proportional { max_oversampling } => {
                if strength > 0.0 {
                    let mult = 1.0 + (max_oversampling - 1.0) * strength.min(5.0) / 5.0;
                    self.sampling_multiplier = mult;
                    self.transition_to(InferenceState::Active);
                    ActivationDecision::ActivateWithRate(mult)
                } else {
                    self.sampling_multiplier = 1.0;
                    self.transition_to(InferenceState::Idle);
                    ActivationDecision::Maintain
                }
            }

            ActivationPolicy::Aggressive => match event.recommended_action {
                PrecursorAction::None => {
                    self.transition_to(InferenceState::Idle);
                    self.sampling_multiplier = 1.0;
                    ActivationDecision::Maintain
                }
                PrecursorAction::IncreaseSampling => {
                    self.transition_to(InferenceState::WarmingUp);
                    self.sampling_multiplier = 1.5;
                    ActivationDecision::WarmUp
                }
                PrecursorAction::PreactivateInference => {
                    self.transition_to(InferenceState::Active);
                    self.sampling_multiplier = 2.0;
                    ActivationDecision::Activate
                }
                PrecursorAction::ActivateInference | PrecursorAction::Alert => {
                    self.transition_to(InferenceState::HighAlert);
                    self.sampling_multiplier = 4.0;
                    ActivationDecision::HighAlert
                }
            },

            ActivationPolicy::Hysteresis {
                activate_threshold,
                deactivate_threshold,
            } => match &self.state {
                InferenceState::Idle | InferenceState::WarmingUp => {
                    if strength >= *activate_threshold {
                        self.transition_to(InferenceState::Active);
                        self.sampling_multiplier = 2.0;
                        ActivationDecision::Activate
                    } else if strength >= *deactivate_threshold {
                        self.transition_to(InferenceState::WarmingUp);
                        self.sampling_multiplier = 1.5;
                        ActivationDecision::WarmUp
                    } else {
                        self.sampling_multiplier = 1.0;
                        ActivationDecision::Maintain
                    }
                }
                InferenceState::Active | InferenceState::HighAlert => {
                    if strength < *deactivate_threshold {
                        self.transition_to(InferenceState::Idle);
                        self.sampling_multiplier = 1.0;
                        ActivationDecision::Cooldown
                    } else if strength >= *activate_threshold {
                        self.transition_to(InferenceState::HighAlert);
                        self.sampling_multiplier = 3.0;
                        ActivationDecision::HighAlert
                    } else {
                        self.sampling_multiplier = 2.0;
                        ActivationDecision::Maintain
                    }
                }
            },
        };

        // Enforce max HighAlert duration to prevent battery drain
        if self.state == InferenceState::HighAlert {
            self.state_duration += 1;
            if self.state_duration > self.max_high_alert_duration {
                warn!(
                    "HighAlert duration exceeded {} windows, forcing cooldown",
                    self.max_high_alert_duration
                );
                self.transition_to(InferenceState::Active);
                self.sampling_multiplier = 2.0;
                return ActivationDecision::Cooldown;
            }
        }

        info!(
            "Activation decision: {:?} → state={:?}, sampling={:.1} Hz",
            decision,
            self.state,
            self.effective_sampling_hz()
        );

        decision
    }

    /// Returns the effective sampling rate given current multiplier.
    pub fn effective_sampling_hz(&self) -> f64 {
        self.baseline_sampling_hz * self.sampling_multiplier
    }

    /// Returns the current inference state.
    pub fn state(&self) -> &InferenceState {
        &self.state
    }

    /// Returns the current sampling multiplier.
    pub fn sampling_multiplier(&self) -> f64 {
        self.sampling_multiplier
    }

    fn transition_to(&mut self, new_state: InferenceState) {
        if self.state != new_state {
            debug!("State transition: {:?} → {:?}", self.state, new_state);
            self.state = new_state;
            self.state_duration = 0;
        }
    }
}

/// Decision returned by the activator.
#[derive(Debug, Clone, PartialEq)]
pub enum ActivationDecision {
    /// Maintain current state
    Maintain,
    /// Warm up inference engine (pre-load model)
    WarmUp,
    /// Activate inference at baseline rate
    Activate,
    /// Activate inference at specified sampling rate multiplier
    ActivateWithRate(f64),
    /// Enter high-alert mode (max resources)
    HighAlert,
    /// Cool down from high-alert to active/idle
    Cooldown,
}

/// Full pipeline: signal → detector → activator → decision.
///
/// This is the top-level integration point for the phonon precursor
/// detection system in arkhe-hubble-ml.
pub struct PhononInferencePipeline {
    detector: crate::phonon::detector::PhononPrecursorDetector,
    activator: InferenceActivator,
}

impl PhononInferencePipeline {
    /// Creates a new pipeline with the given detector config and activation policy.
    pub fn new(
        detector_config: crate::phonon::detector::DetectorConfig,
        policy: ActivationPolicy,
        baseline_sampling_hz: f64,
    ) -> crate::HubbleResult<Self> {
        use crate::phonon::detector::PhononPrecursorDetector;

        let detector = PhononPrecursorDetector::new(detector_config)?;
        let activator = InferenceActivator::new(policy, baseline_sampling_hz, 20);

        Ok(Self {
            detector,
            activator,
        })
    }

    /// Processes a signal window and returns activation decisions.
    pub fn process(&mut self, samples: &[f64]) -> Vec<ActivationDecision> {
        let events = self.detector.process_window(samples);
        events
            .iter()
            .map(|event| self.activator.process_event(event))
            .collect()
    }

    /// Returns the detector's active precursors.
    pub fn active_precursors(&self) -> &[(f64, crate::phonon::precursor::PrecursorSignature)] {
        self.detector.active_precursors()
    }

    /// Returns the current inference state.
    pub fn inference_state(&self) -> &InferenceState {
        self.activator.state()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::phonon::precursor::PrecursorSignature;

    fn dummy_signature(strength: f64) -> PrecursorSignature {
        PrecursorSignature {
            frequency_hz: 50.0,
            initial_frequency_hz: 100.0,
            amplitude: 1.0 + strength * 2.0,
            initial_amplitude: 1.0,
            frequency_drift: -0.5,
            amplitude_trend: 0.3,
            persistence: 1,
            confidence: 1.0,
            first_seen: 0,
            last_seen: 4,
        }
    }

    fn dummy_event(strength: f64) -> PrecursorEvent {
        PrecursorEvent {
            signature: dummy_signature(strength),
            trigger_window: 10,
            recommended_action: PrecursorAction::from_strength(strength),
            estimated_lead_time: Some(5),
        }
    }

    #[test]
    fn test_hysteresis_policy() {
        let policy = ActivationPolicy::Hysteresis {
            activate_threshold: 2.0,
            deactivate_threshold: 0.5,
        };
        let mut activator = InferenceActivator::new(policy, 100.0, 10);

        // Start idle, weak signal — stay idle
        let d1 = activator.process_event(&dummy_event(0.1));
        assert_eq!(d1, ActivationDecision::Maintain);
        assert_eq!(*activator.state(), InferenceState::Idle);

        // Strong signal — activate
        let d2 = activator.process_event(&dummy_event(3.0));
        assert_eq!(d2, ActivationDecision::Activate);
        assert_eq!(*activator.state(), InferenceState::Active);

        // Medium signal — stay active (hysteresis)
        let d3 = activator.process_event(&dummy_event(1.0));
        assert_eq!(d3, ActivationDecision::Maintain);
        assert_eq!(*activator.state(), InferenceState::Active);

        // Very strong — high alert
        let d4 = activator.process_event(&dummy_event(6.0));
        assert_eq!(d4, ActivationDecision::HighAlert);
        assert_eq!(*activator.state(), InferenceState::HighAlert);

        // Weak signal — cooldown
        let d5 = activator.process_event(&dummy_event(0.1));
        assert_eq!(d5, ActivationDecision::Cooldown);
        assert_eq!(*activator.state(), InferenceState::Idle);
    }

    #[test]
    fn test_max_high_alert_duration() {
        let policy = ActivationPolicy::Aggressive;
        let mut activator = InferenceActivator::new(policy, 100.0, 3);

        let event = dummy_event(10.0);

        // Enter HighAlert
        let d1 = activator.process_event(&event);
        assert_eq!(d1, ActivationDecision::HighAlert);

        // Stay in HighAlert for 2 more windows
        let _ = activator.process_event(&event);
        let _ = activator.process_event(&event);

        // 4th window should force cooldown
        let d4 = activator.process_event(&event);
        assert_eq!(d4, ActivationDecision::Cooldown);
        assert!(*activator.state() != InferenceState::HighAlert);
    }
}
