//! Phonon Precursor Detector
//!
//! The main detector that combines spectral mode tracking with precursor
//! pattern recognition. Inspired by the phonon-activated collective hopping
//! mechanism in Cu₇PS₆ (PRX 16, 031046, 2026).
//!
//! ## Algorithm
//!
//! 1. **Windowing**: Split incoming signal into overlapping windows
//! 2. **FFT**: Compute spectrum per window using Hann-windowed Radix-4 FFT
//! 3. **Peak Detection**: Find spectral peaks above amplitude/SNR thresholds
//! 4. **Mode Tracking**: Track peaks across windows by frequency proximity
//! 5. **Precursor Detection**: Identify modes with dω/dt < 0 AND dA/dt > 0
//! 6. **Scoring**: Compute composite strength score for each precursor
//! 7. **Action**: Map strength to PrecursorAction (None → Alert)
//!
//! ## Physical Analogy
//!
//! | Cu₇PS₆ (PRX) | Sensor Edge (Arkhe) |
//! |---|---|
//! | Optical phonon (~3.36 meV) | Low-frequency signal mode |
//! | Phonon softening (ω → 0) | Frequency drift downward |
//! | Amplitude growth (overdamped) | Amplitude trend upward |
//! | Collective hopping triggered | Inference pre-activation |
//! | Superionic transition (510 K) | Critical event detected |

use crate::phonon::modes::{ModeTracker, SpectralMode};
use crate::phonon::precursor::{PrecursorAction, PrecursorEvent, PrecursorSignature};
use crate::{HubbleError, HubbleResult};
use tracing::{debug, info, trace, warn};

/// Configuration for the Phonon Precursor Detector.
#[derive(Debug, Clone)]
pub struct DetectorConfig {
    /// FFT window size (must be power of 2)
    pub window_size: usize,
    /// Hop size between consecutive windows
    pub hop_size: usize,
    /// Sensor sampling rate in Hz
    pub sampling_rate_hz: f64,
    /// Minimum amplitude for peak detection
    pub amplitude_threshold: f64,
    /// Minimum SNR in dB for peak detection
    pub snr_threshold_db: f64,
    /// Maximum frequency to consider as "low-frequency precursor" (Hz)
    pub max_precursor_freq_hz: f64,
    /// Number of windows to track for drift/trend analysis
    pub tracking_window_count: usize,
    /// Frequency proximity tolerance for mode matching (fraction of frequency)
    pub freq_match_tolerance: f64,
    /// Minimum persistence (consecutive windows) to declare a precursor
    pub min_persistence: usize,
    /// Minimum confidence for a valid precursor [0.0, 1.0]
    pub min_confidence: f64,
    /// Minimum relative frequency shift to consider as "softening"
    pub min_relative_shift: f64,
    /// Minimum relative amplitude gain to consider as "amplification"
    pub min_relative_gain: f64,
}

impl Default for DetectorConfig {
    fn default() -> Self {
        Self {
            window_size: 256,
            hop_size: 128,
            sampling_rate_hz: 1000.0,
            amplitude_threshold: 0.05,
            snr_threshold_db: 8.0,
            max_precursor_freq_hz: 100.0, // Focus on low-frequency modes
            tracking_window_count: 8,
            freq_match_tolerance: 0.15, // 15% frequency tolerance
            min_persistence: 3,
            min_confidence: 0.6,
            min_relative_shift: 0.05, // 5% frequency decrease
            min_relative_gain: 0.20,  // 20% amplitude increase
        }
    }
}

/// Phonon Precursor Detector for edge sensor networks.
///
/// Detects low-frequency signal modes that exhibit "softening + amplification"
/// patterns — precursors to critical events in the sensor environment.
pub struct PhononPrecursorDetector {
    config: DetectorConfig,
    tracker: ModeTracker,
    /// Active precursors being tracked: (frequency_key, signature)
    active_precursors: Vec<(f64, PrecursorSignature)>,
    /// Total number of windows processed
    window_count: usize,
}

impl PhononPrecursorDetector {
    /// Creates a new detector with the given configuration.
    pub fn new(config: DetectorConfig) -> HubbleResult<Self> {
        if !config.window_size.is_power_of_two() {
            return Err(HubbleError::Phonon(
                "window_size must be a power of 2".into(),
            ));
        }

        let tracker = ModeTracker::new(
            config.window_size,
            config.hop_size,
            config.sampling_rate_hz,
            config.amplitude_threshold,
            config.snr_threshold_db,
        );

        Ok(Self {
            config,
            tracker,
            active_precursors: Vec::new(),
            window_count: 0,
        })
    }

    /// Processes a single window of samples.
    ///
    /// Returns any precursor events triggered by this window.
    pub fn process_window(&mut self, samples: &[f64]) -> Vec<PrecursorEvent> {
        if samples.len() != self.config.window_size {
            warn!(
                "Sample count {} does not match window_size {}, padding/truncating",
                samples.len(),
                self.config.window_size
            );
        }

        let window = if samples.len() >= self.config.window_size {
            &samples[..self.config.window_size]
        } else {
            // Pad with zeros
            let mut padded = vec![0.0; self.config.window_size];
            padded[..samples.len()].copy_from_slice(samples);
            // Store on stack temporarily — this is inefficient but safe
            // In production, use a ring buffer
            return self.process_window(&padded);
        };

        let modes = self.tracker.process_window(window);
        self.window_count += 1;

        trace!(
            "Window {}: detected {} modes",
            self.window_count,
            modes.len()
        );

        // Update active precursors and detect new ones
        self.update_precursors(&modes);

        // Generate events from precursors that meet thresholds
        self.generate_events()
    }

    /// Processes a continuous signal stream.
    ///
    /// Splits the signal into overlapping windows and processes each.
    pub fn process_stream(&mut self, signal: &[f64]) -> Vec<PrecursorEvent> {
        let mut all_events = Vec::new();
        let window_size = self.config.window_size;
        let hop_size = self.config.hop_size;
        let num_windows = (signal.len().saturating_sub(window_size)) / hop_size + 1;

        for w in 0..num_windows {
            let start = w * hop_size;
            let end = start + window_size;
            if end <= signal.len() {
                let events = self.process_window(&signal[start..end]);
                all_events.extend(events);
            }
        }

        all_events
    }

    /// Updates the active precursor tracking with newly detected modes.
    fn update_precursors(&mut self, modes: &[SpectralMode]) {
        let current_window = self.window_count - 1; // process_window already incremented

        // Filter modes to low-frequency range (precursor candidates)
        let candidate_modes: Vec<&SpectralMode> = modes
            .iter()
            .filter(|m| m.frequency <= self.config.max_precursor_freq_hz)
            .collect();

        // Mark all existing precursors as "not seen this window"
        let mut seen = vec![false; self.active_precursors.len()];

        // Try to match each candidate to an existing precursor
        for mode in &candidate_modes {
            let mut matched = false;

            // To avoid the borrow checker issues, first calculate properties that depend on self
            let drift = self
                .tracker
                .frequency_drift(mode.frequency, self.config.tracking_window_count);
            let trend = self
                .tracker
                .amplitude_trend(mode.frequency, self.config.tracking_window_count);
            let snr = mode.snr;
            let freq = mode.frequency;
            let amp = mode.amplitude;

            // Now do the mutation
            for (i, (freq_key, sig)) in self.active_precursors.iter_mut().enumerate() {
                let freq_diff = (freq - *freq_key).abs();
                let tolerance = self.config.freq_match_tolerance * *freq_key;

                if freq_diff <= tolerance {
                    // Match found — update precursor
                    *freq_key = freq; // Update tracking frequency
                    sig.frequency_hz = freq;
                    sig.amplitude = amp;
                    sig.last_seen = current_window;
                    sig.persistence += 1;

                    // Recompute drift and trend
                    if let Some(d) = drift {
                        sig.frequency_drift = d;
                    }
                    if let Some(t) = trend {
                        sig.amplitude_trend = t;
                    }

                    // Update confidence based on persistence and SNR
                    // (we moved compute_confidence to not need `self` for simplicity)
                    let persistence_factor =
                        (sig.persistence as f64 / self.config.min_persistence as f64).min(1.0);
                    let snr_factor = (snr / self.config.snr_threshold_db).min(2.0) / 2.0;
                    let drift_clarity =
                        sig.frequency_drift.abs() / (sig.frequency_hz * 0.01 + 1e-6);
                    let trend_clarity = sig.amplitude_trend.abs() / (sig.amplitude * 0.01 + 1e-6);

                    sig.confidence = (persistence_factor * 0.3
                        + snr_factor * 0.3
                        + drift_clarity.min(1.0) * 0.2
                        + trend_clarity.min(1.0) * 0.2)
                        .min(1.0);

                    seen[i] = true;
                    matched = true;
                    break;
                }
            }

            if !matched {
                // New precursor candidate
                let new_sig = PrecursorSignature {
                    frequency_hz: mode.frequency,
                    initial_frequency_hz: mode.frequency,
                    amplitude: mode.amplitude,
                    initial_amplitude: mode.amplitude,
                    frequency_drift: 0.0,
                    amplitude_trend: 0.0,
                    persistence: 1,
                    confidence: self.compute_confidence_for_new(mode.snr),
                    first_seen: current_window,
                    last_seen: current_window,
                };

                self.active_precursors.push((mode.frequency, new_sig));
                // We also need to add an entry in the seen array for the newly added precursor
                seen.push(true);

                debug!(
                    "New precursor candidate at {:.2} Hz (SNR: {:.1} dB)",
                    mode.frequency, mode.snr
                );
            }
        }

        // Remove stale precursors (not seen for too long)
        let stale_threshold = self.config.min_persistence.max(3);

        // Find indices of precursors to remove based on seen state and staleness
        let mut to_remove = Vec::new();
        for (i, (freq_key, sig)) in self.active_precursors.iter().enumerate() {
            let keep = seen[i] || (current_window - sig.last_seen) < stale_threshold;
            if !keep {
                debug!("Removing stale precursor at {:.2} Hz", freq_key);
                to_remove.push(i);
            }
        }

        // Remove from highest index to lowest to maintain index validity
        for &i in to_remove.iter().rev() {
            self.active_precursors.remove(i);
        }
    }

    /// Generates precursor events from active precursors that meet thresholds.
    fn generate_events(&mut self) -> Vec<PrecursorEvent> {
        let current_window = self.window_count - 1;
        let mut events = Vec::new();

        for (_, sig) in &self.active_precursors {
            // Check if this precursor meets all criteria
            let meets_softening = sig.is_softening();
            let meets_shift =
                sig.relative_frequency_shift().abs() >= self.config.min_relative_shift;
            let meets_gain = sig.relative_amplitude_gain() >= self.config.min_relative_gain;
            let meets_persistence = sig.persistence >= self.config.min_persistence;
            let meets_confidence = sig.confidence >= self.config.min_confidence;

            if meets_softening && meets_shift && meets_gain && meets_persistence && meets_confidence
            {
                let strength = sig.strength_score();
                let action = PrecursorAction::from_strength(strength);

                if action != PrecursorAction::None {
                    // Estimate lead time based on drift rate
                    let lead_time = if sig.frequency_drift < 0.0 {
                        let windows_to_zero =
                            (sig.frequency_hz / sig.frequency_drift.abs()).ceil() as usize;
                        Some(windows_to_zero)
                    } else {
                        None
                    };

                    info!(
                        "Precursor detected! freq={:.2}Hz, drift={:.4}, trend={:.4}, strength={:.2}, action={:?}",
                        sig.frequency_hz, sig.frequency_drift, sig.amplitude_trend,
                        strength, action
                    );

                    events.push(PrecursorEvent {
                        signature: sig.clone(),
                        trigger_window: current_window,
                        recommended_action: action,
                        estimated_lead_time: lead_time,
                    });
                }
            }
        }

        events
    }

    /// Computes initial confidence for a new precursor.
    fn compute_confidence_for_new(&self, snr: f64) -> f64 {
        let snr_factor = (snr / self.config.snr_threshold_db).min(2.0) / 2.0;
        snr_factor * 0.5 // Low initial confidence until persistence builds
    }

    /// Returns the current active precursors.
    pub fn active_precursors(&self) -> &[(f64, PrecursorSignature)] {
        &self.active_precursors
    }

    /// Returns the total number of windows processed.
    pub fn window_count(&self) -> usize {
        self.window_count
    }

    /// Resets the detector state.
    pub fn reset(&mut self) {
        self.tracker.clear();
        self.active_precursors.clear();
        self.window_count = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    /// Generates a test signal with a softening precursor:
    /// A low-frequency mode that decreases in frequency while increasing in amplitude.
    fn generate_softening_signal(
        fs: f64,
        duration_s: f64,
        initial_freq: f64,
        final_freq: f64,
        initial_amp: f64,
        final_amp: f64,
    ) -> Vec<f64> {
        let num_samples = (duration_s * fs) as usize;
        let mut signal = vec![0.0; num_samples];

        for i in 0..num_samples {
            let t = i as f64 / fs;
            let progress = t / duration_s;

            // Linear interpolation of frequency and amplitude
            let freq = initial_freq + (final_freq - initial_freq) * progress;
            let amp = initial_amp + (final_amp - initial_amp) * progress;

            // Add some noise
            let noise = 0.02 * (2.0 * PI * 17.3 * t).sin() * (2.0 * PI * 43.7 * t).cos();

            signal[i] = amp * (2.0 * PI * freq * t).sin() + noise;
        }

        signal
    }

    #[test]
    fn test_detect_softening_precursor() {
        let fs = 1000.0;
        let config = DetectorConfig {
            window_size: 256,
            hop_size: 128,
            sampling_rate_hz: fs,
            amplitude_threshold: 0.1,
            snr_threshold_db: 6.0,
            max_precursor_freq_hz: 100.0,
            tracking_window_count: 6,
            freq_match_tolerance: 0.2,
            min_persistence: 3,
            min_confidence: 0.5,
            min_relative_shift: 0.03,
            min_relative_gain: 0.10,
        };

        let mut detector = PhononPrecursorDetector::new(config).unwrap();

        // Generate signal: 60 Hz → 45 Hz, amplitude 0.5 → 1.5 over 5 seconds
        let signal = generate_softening_signal(fs, 5.0, 60.0, 45.0, 0.5, 1.5);

        let events = detector.process_stream(&signal);

        // Should detect at least one precursor event
        assert!(!events.is_empty(), "Expected precursor detection, got none");

        let event = &events[0];
        assert!(event.signature.is_softening(), "Expected softening pattern");
        assert!(
            event.signature.frequency_drift < 0.0,
            "Expected negative drift"
        );
        assert!(
            event.signature.amplitude_trend > 0.0,
            "Expected positive trend"
        );
        assert!(
            event.recommended_action == PrecursorAction::PreactivateInference
                || event.recommended_action == PrecursorAction::ActivateInference
                || event.recommended_action == PrecursorAction::Alert
                || event.recommended_action == PrecursorAction::IncreaseSampling,
            "Expected active action, got {:?}",
            event.recommended_action
        );
    }

    #[test]
    fn test_no_false_positives_on_stationary_signal() {
        let fs = 1000.0;
        let config = DetectorConfig::default();
        let mut detector = PhononPrecursorDetector::new(config).unwrap();

        // Pure 50 Hz sine wave — no softening, no amplification
        let mut signal = vec![0.0; 2048];
        for i in 0..2048 {
            signal[i] = (2.0 * PI * 50.0 * i as f64 / fs).sin();
        }

        let events = detector.process_stream(&signal);

        // Should not trigger any action beyond None/IncreaseSampling
        let active_events: Vec<_> = events
            .iter()
            .filter(|e| {
                e.recommended_action != PrecursorAction::None
                    && e.recommended_action != PrecursorAction::IncreaseSampling
            })
            .collect();

        assert!(
            active_events.is_empty(),
            "Expected no active precursors on stationary signal"
        );
    }
}
