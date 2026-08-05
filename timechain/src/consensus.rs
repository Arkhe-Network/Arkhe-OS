use crate::retro::EchoSignal;
use num_complex::Complex64;
use std::collections::HashMap;
use std::f64::consts::PI;

pub struct ConsensusEngine {
    pub finality_threshold: f64,
    pub received_echos: HashMap<u64, Vec<EchoSignal>>, // height -> list
}

impl ConsensusEngine {
    pub fn new(threshold: f64) -> Self {
        Self {
            finality_threshold: threshold,
            received_echos: HashMap::new(),
        }
    }

    pub fn add_echo(&mut self, echo: EchoSignal) {
        self.received_echos
            .entry(echo.origin_height)
            .or_default()
            .push(echo);
    }

    pub fn check_finality(&self, height: u64, local_phase: f64) -> bool {
        let default_vec = vec![];
        let echos = self.received_echos.get(&height).unwrap_or(&default_vec);
        if echos.len() < 3 {
            return false;
        } // need at least 3
        let mut complex_sum = Complex64::new(0.0, 0.0);
        for echo in echos {
            let amp = echo.strength;
            let phase = echo.predicted_helicity % (2.0 * PI);
            // relative to local phase
            let diff = (phase - local_phase).rem_euclid(2.0 * PI);
            complex_sum += Complex64::new(amp * diff.cos(), amp * diff.sin());
        }
        let interference = complex_sum.norm();
        interference > self.finality_threshold
    }
}
