//! Data structures for phonon precursor events.
//!
//! A precursor signature captures the "softening + amplification" pattern
//! observed in Cu₇PS₆ before collective hopping: phonon modes decrease in
//! frequency while increasing in amplitude as the system approaches criticality.

use serde::{Deserialize, Serialize};

/// Signature of a detected phonon precursor.
///
/// Analogous to the soft optical phonon (~3.36 meV) in Cu₇PS₆ that precedes
/// the superionic transition at 510 K. In sensor networks, this represents
/// a low-frequency mode exhibiting pre-critical behavior.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PrecursorSignature {
    /// Frequency of the precursor mode (Hz)
    pub frequency_hz: f64,
    /// Initial frequency when first tracked (Hz)
    pub initial_frequency_hz: f64,
    /// Current amplitude (normalized)
    pub amplitude: f64,
    /// Initial amplitude when first tracked
    pub initial_amplitude: f64,
    /// Frequency drift rate (Hz per window)
    pub frequency_drift: f64,
    /// Amplitude trend (amplitude units per window)
    pub amplitude_trend: f64,
    /// Number of consecutive windows this precursor has been tracked
    pub persistence: usize,
    /// Confidence score [0.0, 1.0] — how strongly this matches the precursor pattern
    pub confidence: f64,
    /// Timestamp of first detection (window index)
    pub first_seen: usize,
    /// Timestamp of latest detection (window index)
    pub last_seen: usize,
}

impl PrecursorSignature {
    /// Returns true if this precursor exhibits the classic "softening" pattern:
    /// frequency decreasing (dω/dt < 0) AND amplitude increasing (dA/dt > 0).
    ///
    /// This is the direct analog of the phonon softening → collective hopping
    /// mechanism in Cu₇PS₆ (PRX 16, 031046).
    pub fn is_softening(&self) -> bool {
        self.frequency_drift < 0.0 && self.amplitude_trend > 0.0
    }

    /// Returns the relative frequency shift: Δω / ω₀.
    pub fn relative_frequency_shift(&self) -> f64 {
        if self.initial_frequency_hz.abs() < 1e-12 {
            return 0.0;
        }
        (self.frequency_hz - self.initial_frequency_hz) / self.initial_frequency_hz
    }

    /// Returns the relative amplitude gain: ΔA / A₀.
    pub fn relative_amplitude_gain(&self) -> f64 {
        if self.initial_amplitude.abs() < 1e-12 {
            return 0.0;
        }
        (self.amplitude - self.initial_amplitude) / self.initial_amplitude
    }

    /// Computes a composite precursor strength score.
    ///
    /// Higher score = stronger precursor signal.
    /// Formula: |Δω/ω₀| × (ΔA/A₀) × persistence × confidence
    pub fn strength_score(&self) -> f64 {
        let freq_factor = self.relative_frequency_shift().abs();
        let amp_factor = self.relative_amplitude_gain().max(0.0);
        let persistence_factor = (self.persistence as f64).sqrt();

        freq_factor * amp_factor * persistence_factor * self.confidence
    }
}

/// A detected precursor event, ready for downstream action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PrecursorEvent {
    /// The precursor signature at the time of detection
    pub signature: PrecursorSignature,
    /// Window index when the event was triggered
    pub trigger_window: usize,
    /// Recommended action based on precursor strength
    pub recommended_action: PrecursorAction,
    /// Estimated time (in windows) until the main event
    pub estimated_lead_time: Option<usize>,
}

/// Recommended action when a precursor is detected.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PrecursorAction {
    /// No action — precursor too weak or ambiguous
    None,
    /// Increase sampling rate to capture more detail
    IncreaseSampling,
    /// Pre-activate inference engine (warm up model)
    PreactivateInference,
    /// Full activation — trigger inference immediately
    ActivateInference,
    /// Alert — send high-priority telemetry packet
    Alert,
}

impl PrecursorAction {
    /// Maps a strength score to an action.
    ///
    /// Thresholds are configurable; these are defaults based on Cu₇PS₆
    /// criticality analysis (σ_FSO > 0.9 regime).
    pub fn from_strength(score: f64) -> Self {
        match score {
            s if s > 5.0 => PrecursorAction::Alert,
            s if s > 2.0 => PrecursorAction::ActivateInference,
            s if s > 1.0 => PrecursorAction::PreactivateInference,
            s if s > 0.3 => PrecursorAction::IncreaseSampling,
            _ => PrecursorAction::None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_softening_pattern() {
        let sig = PrecursorSignature {
            frequency_hz: 45.0,
            initial_frequency_hz: 50.0,
            amplitude: 2.5,
            initial_amplitude: 1.0,
            frequency_drift: -0.5,
            amplitude_trend: 0.3,
            persistence: 5,
            confidence: 0.9,
            first_seen: 0,
            last_seen: 4,
        };
        assert!(sig.is_softening());
        assert!((sig.relative_frequency_shift() - (-0.1)).abs() < 1e-6);
        assert!((sig.relative_amplitude_gain() - 1.5).abs() < 1e-6);
        assert!(sig.strength_score() > 0.0);
    }

    #[test]
    fn test_action_mapping() {
        assert_eq!(PrecursorAction::from_strength(0.1), PrecursorAction::None);
        assert_eq!(
            PrecursorAction::from_strength(0.5),
            PrecursorAction::IncreaseSampling
        );
        assert_eq!(
            PrecursorAction::from_strength(1.5),
            PrecursorAction::PreactivateInference
        );
        assert_eq!(
            PrecursorAction::from_strength(3.0),
            PrecursorAction::ActivateInference
        );
        assert_eq!(PrecursorAction::from_strength(6.0), PrecursorAction::Alert);
    }
}
