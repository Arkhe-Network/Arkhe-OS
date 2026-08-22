//! Spectral mode analysis using FFT.
//!
//! Decomposes time-series sensor data into frequency components and tracks
//! their evolution across windows — analogous to phonon dispersion tracking
//! in inelastic neutron scattering (INS).

use num_complex::Complex;
use rustfft::{algorithm::Radix4, Fft, FftDirection};
use std::sync::Arc;

/// A detected spectral mode with frequency, amplitude, and phase.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SpectralMode {
    /// Frequency in Hz (or normalized frequency if sampling rate = 1)
    pub frequency: f64,
    /// Amplitude (magnitude of complex FFT coefficient)
    pub amplitude: f64,
    /// Phase in radians
    pub phase: f64,
    /// Signal-to-noise ratio of this mode relative to spectral floor
    pub snr: f64,
    /// Window index where this mode was detected
    pub window_index: usize,
}

/// Tracks the evolution of spectral modes across time windows.
///
/// Analogous to tracking phonon linewidths and frequencies across temperature
/// in a QENS experiment — but here "temperature" is replaced by "time".
pub struct ModeTracker {
    fft: Arc<dyn Fft<f64>>,
    window_size: usize,
    hop_size: usize,
    sampling_rate_hz: f64,
    /// History of modes per window: modes[window_index] = Vec<SpectralMode>
    history: Vec<Vec<SpectralMode>>,
    /// Minimum amplitude for a peak to be considered a mode
    amplitude_threshold: f64,
    /// Minimum SNR (dB) for peak detection
    snr_threshold_db: f64,
}

impl ModeTracker {
    /// Creates a new ModeTracker.
    ///
    /// # Arguments
    /// * `window_size` — FFT size (must be power of 2 for Radix4)
    /// * `hop_size` — Samples between consecutive windows (overlap = window_size - hop_size)
    /// * `sampling_rate_hz` — Sensor sampling rate
    /// * `amplitude_threshold` — Minimum absolute amplitude for peak detection
    /// * `snr_threshold_db` — Minimum SNR in dB for peak detection
    pub fn new(
        window_size: usize,
        hop_size: usize,
        sampling_rate_hz: f64,
        amplitude_threshold: f64,
        snr_threshold_db: f64,
    ) -> Self {
        assert!(
            window_size.is_power_of_two(),
            "window_size must be power of 2"
        );
        assert!(
            hop_size > 0 && hop_size <= window_size,
            "hop_size must be in (0, window_size]"
        );

        let fft: Arc<dyn Fft<f64>> = Arc::new(Radix4::new(window_size, FftDirection::Forward));

        Self {
            fft,
            window_size,
            hop_size,
            sampling_rate_hz,
            history: Vec::new(),
            amplitude_threshold,
            snr_threshold_db,
        }
    }

    /// Processes a new window of samples and extracts spectral modes.
    ///
    /// Returns the detected modes for this window.
    pub fn process_window(&mut self, samples: &[f64]) -> Vec<SpectralMode> {
        assert_eq!(
            samples.len(),
            self.window_size,
            "sample count must equal window_size"
        );

        // Apply Hann window to reduce spectral leakage
        let windowed: Vec<Complex<f64>> = samples
            .iter()
            .enumerate()
            .map(|(i, &s)| {
                let hann = 0.5
                    * (1.0
                        - (2.0 * std::f64::consts::PI * i as f64
                            / (self.window_size as f64 - 1.0))
                            .cos());
                Complex::new(s * hann, 0.0)
            })
            .collect();

        // FFT
        let mut spectrum = windowed.clone();
        self.fft.process(&mut spectrum);

        // Compute magnitude spectrum (only positive frequencies)
        let half = self.window_size / 2;
        let magnitudes: Vec<f64> = spectrum[..half].iter().map(|c| c.norm()).collect();

        // Compute spectral floor (median of magnitudes, excluding DC)
        let mut sorted_mags = magnitudes[1..].to_vec();
        sorted_mags.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let floor = sorted_mags
            .get(sorted_mags.len() / 2)
            .copied()
            .unwrap_or(1e-10);

        // Find peaks
        let mut modes = Vec::new();
        let freq_resolution = self.sampling_rate_hz / self.window_size as f64;

        for i in 1..(half - 1) {
            let prev = magnitudes[i - 1];
            let curr = magnitudes[i];
            let next = magnitudes[i + 1];

            // Peak detection: local maximum
            if curr > prev && curr > next && curr > self.amplitude_threshold {
                // Parabolic interpolation for sub-bin frequency accuracy
                let alpha = prev.ln();
                let beta = curr.ln();
                let gamma = next.ln();
                let p = 0.5 * (alpha - gamma) / (alpha - 2.0 * beta + gamma);

                let freq = (i as f64 + p) * freq_resolution;
                let amp = curr;
                let snr_db = 20.0 * (curr / floor).log10();

                if snr_db >= self.snr_threshold_db {
                    // Phase from complex coefficient
                    let phase = spectrum[i].arg();

                    modes.push(SpectralMode {
                        frequency: freq,
                        amplitude: amp,
                        phase,
                        snr: snr_db,
                        window_index: self.history.len(),
                    });
                }
            }
        }

        // Sort by amplitude descending
        modes.sort_by(|a, b| b.amplitude.partial_cmp(&a.amplitude).unwrap());

        self.history.push(modes.clone());
        modes
    }

    /// Processes an entire signal by sliding the window.
    pub fn process_signal(&mut self, signal: &[f64]) -> Vec<Vec<SpectralMode>> {
        let num_windows = (signal.len().saturating_sub(self.window_size)) / self.hop_size + 1;

        for w in 0..num_windows {
            let start = w * self.hop_size;
            let end = start + self.window_size;
            if end <= signal.len() {
                let window = &signal[start..end];
                self.process_window(window);
            }
        }

        self.history.clone()
    }

    /// Returns the history of tracked modes.
    pub fn history(&self) -> &[Vec<SpectralMode>] {
        &self.history
    }

    /// Clears the history.
    pub fn clear(&mut self) {
        self.history.clear();
    }

    /// Computes the frequency drift (dω/dt) for a specific mode across windows.
    ///
    /// Tracks the mode with frequency closest to `target_freq` and returns
    /// the linear regression slope of frequency vs window index.
    pub fn frequency_drift(&self, target_freq: f64, window_range: usize) -> Option<f64> {
        let n = self.history.len();
        if n < 2 {
            return None;
        }

        let start = n.saturating_sub(window_range);
        let mut points: Vec<(f64, f64)> = Vec::new(); // (window_index, frequency)

        for (wi, modes) in self.history[start..].iter().enumerate() {
            let actual_wi = (start + wi) as f64;
            // Find mode closest to target_freq
            if let Some(mode) = modes.iter().min_by(|a, b| {
                (a.frequency - target_freq)
                    .abs()
                    .partial_cmp(&(b.frequency - target_freq).abs())
                    .unwrap()
            }) {
                if (mode.frequency - target_freq).abs() < 0.1 * target_freq {
                    points.push((actual_wi, mode.frequency));
                }
            }
        }

        if points.len() < 2 {
            return None;
        }

        // Linear regression: slope = Cov(x,y) / Var(x)
        let n = points.len() as f64;
        let mean_x = points.iter().map(|(x, _)| x).sum::<f64>() / n;
        let mean_y = points.iter().map(|(_, y)| y).sum::<f64>() / n;

        let cov_xy: f64 = points
            .iter()
            .map(|(x, y)| (x - mean_x) * (y - mean_y))
            .sum();
        let var_x: f64 = points.iter().map(|(x, _)| (x - mean_x).powi(2)).sum();

        if var_x.abs() < 1e-12 {
            return None;
        }

        Some(cov_xy / var_x)
    }

    /// Computes the amplitude trend (dA/dt) for a specific mode across windows.
    pub fn amplitude_trend(&self, target_freq: f64, window_range: usize) -> Option<f64> {
        let n = self.history.len();
        if n < 2 {
            return None;
        }

        let start = n.saturating_sub(window_range);
        let mut points: Vec<(f64, f64)> = Vec::new();

        for (wi, modes) in self.history[start..].iter().enumerate() {
            let actual_wi = (start + wi) as f64;
            if let Some(mode) = modes.iter().min_by(|a, b| {
                (a.frequency - target_freq)
                    .abs()
                    .partial_cmp(&(b.frequency - target_freq).abs())
                    .unwrap()
            }) {
                if (mode.frequency - target_freq).abs() < 0.1 * target_freq {
                    points.push((actual_wi, mode.amplitude));
                }
            }
        }

        if points.len() < 2 {
            return None;
        }

        let n = points.len() as f64;
        let mean_x = points.iter().map(|(x, _)| x).sum::<f64>() / n;
        let mean_y = points.iter().map(|(_, y)| y).sum::<f64>() / n;

        let cov_xy: f64 = points
            .iter()
            .map(|(x, y)| (x - mean_x) * (y - mean_y))
            .sum();
        let var_x: f64 = points.iter().map(|(x, _)| (x - mean_x).powi(2)).sum();

        if var_x.abs() < 1e-12 {
            return None;
        }

        Some(cov_xy / var_x)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn test_detect_single_tone() {
        let fs = 1000.0;
        let window_size = 256;
        let mut tracker = ModeTracker::new(window_size, window_size / 2, fs, 0.1, 10.0);

        // Generate 100 Hz sine wave
        let mut signal = vec![0.0; window_size];
        for i in 0..window_size {
            signal[i] = (2.0 * PI * 100.0 * i as f64 / fs).sin();
        }

        let modes = tracker.process_window(&signal);
        assert!(!modes.is_empty());

        // Should detect ~100 Hz
        let dominant = &modes[0];
        assert!(
            (dominant.frequency - 100.0).abs() < 5.0,
            "Expected ~100 Hz, got {}",
            dominant.frequency
        );
        assert!(
            dominant.amplitude > 50.0,
            "Amplitude too low: {}",
            dominant.amplitude
        );
    }

    #[test]
    fn test_frequency_drift() {
        let fs = 1000.0;
        let window_size = 256;
        let mut tracker = ModeTracker::new(window_size, window_size, fs, 0.1, 5.0);

        // Generate chirp: frequency decreases from 200 Hz to 150 Hz
        for w in 0..10 {
            let freq = 200.0 - 5.0 * w as f64;
            let mut window = vec![0.0; window_size];
            for i in 0..window_size {
                let t = (w * window_size + i) as f64 / fs;
                window[i] = (2.0 * PI * freq * t).sin();
            }
            tracker.process_window(&window);
        }

        let drift = tracker.frequency_drift(175.0, 10);
        assert!(drift.is_some());
        assert!(drift.unwrap() < 0.0, "Expected negative drift (softening)");
    }
}
