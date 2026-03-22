//! Voyager-1LD Phase Clock
//!
//! Implements the phase-synchronized clock based on Voyager-1's distance from Earth.
//! In November 2026, Voyager-1 will reach exactly 1 light-day, establishing
//! a cosmic metronome at 5.787 μHz with π rad phase accumulation per day.

use anyhow::Result;
use chrono::{TimeZone, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoyagerClock {
    speed_of_light: f64,     // m/s (SI exact: 299,792,458)
    seconds_per_day: f64,    // 86,400 s
    light_day_distance: f64, // 2.59e13 m
    resonance_freq: f64,     // 5.787e-6 Hz
    omega_resonance: f64,    // rad/s
    reference_epoch: i64,    // Unix timestamp of reference
}

impl VoyagerClock {
    pub fn new() -> Result<Self> {
        let speed_of_light = 299_792_458.0;
        let seconds_per_day = 86_400.0;
        let light_day_distance = speed_of_light * seconds_per_day;
        let resonance_freq = speed_of_light / (2.0 * light_day_distance);
        let omega_resonance = 2.0 * std::f64::consts::PI * resonance_freq;

        // Reference epoch: 2026-03-22 (current date)
        let reference_epoch = chrono::Utc
            .with_ymd_and_hms(2026, 3, 22, 0, 0, 0)
            .unwrap()
            .timestamp();

        Ok(Self {
            speed_of_light,
            seconds_per_day,
            light_day_distance,
            resonance_freq,
            omega_resonance,
            reference_epoch,
        })
    }

    pub fn speed_of_light(&self) -> f64 {
        self.speed_of_light
    }

    pub fn light_day_distance(&self) -> f64 {
        self.light_day_distance
    }

    pub fn resonance_frequency(&self) -> f64 {
        self.resonance_freq
    }

    pub fn omega_resonance(&self) -> f64 {
        self.omega_resonance
    }

    /// Calculate current phase in radians
    pub fn current_phase(&self) -> f64 {
        let now = chrono::Utc::now().timestamp();
        let delta_t = (now - self.reference_epoch) as f64;
        self.omega_resonance * delta_t
    }

    /// Calculate phase accumulated since a given timestamp
    pub fn phase_since(&self, timestamp: i64) -> f64 {
        let now = chrono::Utc::now().timestamp();
        let delta_t = (now - timestamp) as f64;
        self.omega_resonance * delta_t
    }

    /// Calculate phase in degrees
    pub fn current_phase_degrees(&self) -> f64 {
        self.current_phase().to_degrees()
    }

    /// Check if phase is at resonance (within threshold)
    pub fn is_at_resonance(&self, threshold_degrees: f64) -> bool {
        let phase_degrees = self.current_phase_degrees().rem_euclid(360.0);
        let distance_from_pi = (phase_degrees - 180.0).abs();
        distance_from_pi < threshold_degrees
    }

    /// Get the time until next resonance (phase = π)
    pub fn time_until_resonance(&self) -> f64 {
        let current_phase = self.current_phase();
        let phase_per_day = self.omega_resonance * self.seconds_per_day;
        let days_to_resonance =
            (std::f64::consts::PI - current_phase.rem_euclid(std::f64::consts::PI)) / phase_per_day;
        days_to_resonance * self.seconds_per_day
    }

    /// Calculate phase for a specific delta time
    pub fn phase_for_delta(&self, delta_seconds: f64) -> f64 {
        self.omega_resonance * delta_seconds
    }

    /// Get clock state as JSON
    pub fn state_json(&self) -> serde_json::Value {
        serde_json::json!({
            "speed_of_light_m_s": self.speed_of_light,
            "light_day_distance_m": self.light_day_distance,
            "resonance_frequency_hz": self.resonance_freq,
            "omega_resonance_rad_s": self.omega_resonance,
            "current_phase_rad": self.current_phase(),
            "current_phase_deg": self.current_phase_degrees(),
            "is_at_resonance": self.is_at_resonance(1.0),
            "time_until_resonance_s": self.time_until_resonance(),
        })
    }
}

impl Default for VoyagerClock {
    fn default() -> Self {
        Self::new().expect("Failed to initialize Voyager clock")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resonance_frequency() {
        let clock = VoyagerClock::new().unwrap();
        let expected_f_res = 5.787e-6;
        assert!((clock.resonance_freq - expected_f_res).abs() < 1e-9);
    }

    #[test]
    fn test_phase_per_day() {
        let clock = VoyagerClock::new().unwrap();
        let phase_per_day = clock.phase_for_delta(clock.seconds_per_day);
        assert!((phase_per_day - std::f64::consts::PI).abs() < 1e-6);
    }
}
