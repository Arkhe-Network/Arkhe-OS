//! Integration test: Phonon Precursor Detection Pipeline
//!
//! Simulates a realistic sensor scenario where a precursor is detected
//! before a critical event, triggering inference pre-activation.

use arkhe_hubble_ml::phonon::{
    activation::{ActivationPolicy, InferenceState, PhononInferencePipeline},
    detector::{DetectorConfig, PhononPrecursorDetector},
};
use std::f64::consts::PI;

/// Generates a realistic sensor signal with three phases:
/// 1. Baseline (0-2s): stable 50 Hz mode, low amplitude
/// 2. Precursor (2-4s): 50 Hz → 38 Hz softening, amplitude 0.3 → 1.2
/// 3. Event (4-5s): broadband burst (simulated critical event)
fn generate_sensor_scenario(fs: f64) -> Vec<f64> {
    let total_samples = (fs * 5.0) as usize;
    let mut signal = vec![0.0; total_samples];

    for i in 0..total_samples {
        let t = i as f64 / fs;

        let (freq, amp, noise_level) = if t < 2.0 {
            // Phase 1: Baseline
            (50.0, 0.3, 0.05)
        } else if t < 4.0 {
            // Phase 2: Precursor — softening + amplification
            let progress = (t - 2.0) / 2.0;
            let f = 50.0 - 12.0 * progress; // 50 → 38 Hz
            let a = 0.3 + 0.9 * progress; // 0.3 → 1.2
            (f, a, 0.08)
        } else {
            // Phase 3: Event — broadband burst
            let burst = (2.0 * PI * 120.0 * t).sin() * 0.5 + (2.0 * PI * 80.0 * t).sin() * 0.3;
            signal[i] = burst;
            continue;
        };

        let carrier = amp * (2.0 * PI * freq * t).sin();
        let noise = noise_level * (2.0 * PI * 17.0 * t).sin() * (2.0 * PI * 43.0 * t).cos();
        signal[i] = carrier + noise;
    }

    signal
}

#[test]
fn test_full_precursor_pipeline() {
    let fs = 1000.0;
    let signal = generate_sensor_scenario(fs);

    let config = DetectorConfig {
        window_size: 256,
        hop_size: 64, // 75% overlap for better time resolution
        sampling_rate_hz: fs,
        amplitude_threshold: 0.1,
        snr_threshold_db: 5.0,
        max_precursor_freq_hz: 100.0,
        tracking_window_count: 8,
        freq_match_tolerance: 0.25,
        min_persistence: 4,
        min_confidence: 0.5,
        min_relative_shift: 0.05,
        min_relative_gain: 0.20,
    };

    let policy = ActivationPolicy::Hysteresis {
        activate_threshold: 1.5,
        deactivate_threshold: 0.4,
    };

    let mut pipeline = PhononInferencePipeline::new(config, policy, fs).unwrap();

    // Process the signal
    let mut decisions = Vec::new();
    let window_size = 256;
    let hop_size = 64;
    let num_windows = (signal.len() - window_size) / hop_size + 1;

    for w in 0..num_windows {
        let start = w * hop_size;
        let window = &signal[start..start + window_size];
        let mut d = pipeline.process(window);
        decisions.append(&mut d);
    }

    // Analyze decisions
    let activation_decisions: Vec<_> = decisions
        .iter()
        .filter(|d| **d != arkhe_hubble_ml::phonon::activation::ActivationDecision::Maintain)
        .collect();

    println!("Total windows processed: {}", num_windows);
    println!("Non-maintain decisions: {}", activation_decisions.len());
    println!(
        "Active precursors at end: {}",
        pipeline.active_precursors().len()
    );
    println!("Final inference state: {:?}", pipeline.inference_state());

    // Assertions
    assert!(
        !activation_decisions.is_empty(),
        "Expected at least one activation decision"
    );

    // The precursor should trigger before the event (window ~80-100 for 4s event)
    // With 64-sample hop at 1000 Hz, each window is 64ms. Event at 4s = window ~62.
    // Precursor detected a few windows before.

    let final_state = pipeline.inference_state();
    assert!(
        *final_state == InferenceState::Active || *final_state == InferenceState::HighAlert,
        "Expected active or high-alert state after precursor detection, got {:?}",
        final_state
    );
}

#[test]
fn test_precursor_lead_time() {
    let fs = 1000.0;
    let signal = generate_sensor_scenario(fs);

    let config = DetectorConfig {
        window_size: 256,
        hop_size: 64,
        sampling_rate_hz: fs,
        amplitude_threshold: 0.1,
        snr_threshold_db: 5.0,
        max_precursor_freq_hz: 100.0,
        tracking_window_count: 10,
        freq_match_tolerance: 0.2,
        min_persistence: 3,
        min_confidence: 0.4,
        min_relative_shift: 0.03,
        min_relative_gain: 0.15,
    };

    let mut detector = PhononPrecursorDetector::new(config).unwrap();
    let events = detector.process_stream(&signal);

    // Check that at least one event has an estimated lead time
    let events_with_lead: Vec<_> = events
        .iter()
        .filter(|e| e.estimated_lead_time.is_some())
        .collect();

    assert!(
        !events_with_lead.is_empty(),
        "Expected at least one event with estimated lead time"
    );

    for event in &events_with_lead {
        let lead = event.estimated_lead_time.unwrap();
        println!(
            "Precursor at window {}: lead time = {} windows ({:.0} ms), action = {:?}",
            event.trigger_window,
            lead,
            lead as f64 * 64.0, // 64 ms per window at 1000 Hz with hop=64
            event.recommended_action
        );
        assert!(lead > 0, "Lead time should be positive");
    }
}
