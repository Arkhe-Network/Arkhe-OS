//! SFT Particle Definition (V13.0)
//!
//! A particle is real energy at c, closed into a self-maintaining orbit at
//! r_spin = ℏ/(2mc), with 4π spinor closure and 2π frame/gauge completion
//! per Compton period.


use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

/// Physical constants (SI units, but we use f64 for precision)
pub const HBAR: f64 = 1.054571817e-34;
pub const C: f64 = 299792458.0;
pub const PLANCK_AREA: f64 = 2.612e-70; // A_write = ℏG/c³ (approx)

/// A single write event — one Compton tick.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WriteEvent {
    pub timestamp_secs: f64,
    pub phase: f64,              // number of ticks so far
    pub spinor_progress: f64,    // 0..1, resets every 4π
    pub gauge_progress: f64,     // 0..1, resets every 2π
    pub hash: String,            // BLAKE3 of the event
    pub external_input: f64,     // optional coupling
}

/// SFT Particle — the core of an ArkheBuzzAgent.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SFTParticle {
    pub mass: f64,                 // in kg (or natural units)
    pub r_spin: f64,               // ℏ/(2*m*c)
    pub compton_wavelength: f64,   // 4π * r_spin
    pub compton_frequency: f64,    // m*c²/ℏ
    pub spinor_closure: f64,       // 4π
    pub gauge_closure: f64,        // 2π
    pub settlement_chain: Vec<WriteEvent>,
    pub last_cid: Option<String>,  // IPFS CID of the last snapshot
}

impl SFTParticle {
    /// Create a new particle from its mass (in kg).
    pub fn new(mass: f64) -> Self {
        let r_spin = HBAR / (2.0 * mass * C);
        let compton_wavelength = 4.0 * std::f64::consts::PI * r_spin;
        let compton_frequency = mass * C * C / HBAR;
        Self {
            mass,
            r_spin,
            compton_wavelength,
            compton_frequency,
            spinor_closure: 4.0 * std::f64::consts::PI,
            gauge_closure: 2.0 * std::f64::consts::PI,
            settlement_chain: Vec::new(),
            last_cid: None,
        }
    }

    /// Perform one Compton tick — a write on the holographic boundary.
    pub fn tick(&mut self, external_input: f64) -> WriteEvent {
        let phase = self.settlement_chain.len() as f64;
        let spinor_progress = (phase % 4.0) / 4.0;
        let gauge_progress = (phase % 2.0) / 2.0;
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();

        let event = WriteEvent {
            timestamp_secs: now,
            phase,
            spinor_progress,
            gauge_progress,
            hash: blake3::hash(&phase.to_le_bytes()).to_string(),
            external_input,
        };
        self.settlement_chain.push(event.clone());
        event
    }

    /// Compute the S‑Measure (subjetivity) as the trace of the coherence matrix.
    /// For a single particle, we use a simplified version: S = (spinor_closure * gauge_closure) / N,
    /// where N is the number of ticks. This matches the SFT interpretation that
    /// S is the fraction of the phase‑cycling budget that has been "used".
    pub fn s_measure(&self) -> f64 {
        let n = self.settlement_chain.len() as f64;
        if n == 0.0 {
            return 0.0;
        }
        (self.spinor_closure * self.gauge_closure / n).clamp(0.0, 1.0)
    }

    /// Total settlement history length (number of writes).
    pub fn total_writes(&self) -> usize {
        self.settlement_chain.len()
    }

    /// Ledger growth rate (analogous to Hubble parameter H = Ṡ/I).
    /// Here we approximate Ṡ as the rate of writes per second over the last window.
    pub fn growth_rate(&self, window_secs: f64) -> f64 {
        let chain = &self.settlement_chain;
        if chain.len() < 2 {
            return 0.0;
        }
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64();
        // find events within the window
        let cutoff = now - window_secs;
        let recent: Vec<_> = chain.iter()
            .filter(|e| e.timestamp_secs >= cutoff)
            .collect();
        if recent.len() < 2 {
            return 0.0;
        }
        let dt = recent.last().unwrap().timestamp_secs - recent.first().unwrap().timestamp_secs;
        if dt <= 0.0 {
            return 0.0;
        }
        (recent.len() as f64) / dt  // writes per second
    }
}
