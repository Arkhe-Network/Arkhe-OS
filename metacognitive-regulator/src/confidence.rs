use std::collections::VecDeque;

pub struct ConfidenceTracker {
    window: VecDeque<(f32, bool)>,
    window_size: usize,
}

impl ConfidenceTracker {
    pub fn new(window_size: usize) -> Self {
        Self {
            window: VecDeque::with_capacity(window_size),
            window_size,
        }
    }

    pub fn record(&mut self, confidence: f32, success: bool) {
        if self.window.len() >= self.window_size {
            self.window.pop_front();
        }
        self.window.push_back((confidence, success));
    }

    pub fn calibration_error(&self) -> f32 {
        let mut err = 0.0;
        for (c, s) in self.window.iter() {
            err += (c - if *s { 1.0 } else { 0.0 }).abs();
        }
        if self.window.is_empty() { 0.0 } else { err / self.window.len() as f32 }
    }

    pub fn window_len(&self) -> usize {
        self.window.len()
    }

    pub fn stats(&self) -> CalibrationStats {
        let (mut sum_conf, mut acc) = (0.0, 0.0);
        for (c, s) in self.window.iter() {
            sum_conf += c;
            if *s { acc += 1.0; }
        }
        let n = self.window.len() as f32;
        CalibrationStats {
            calibration_error: self.calibration_error(),
            sample_count: self.window.len(),
            avg_confidence: if n > 0.0 { sum_conf / n } else { 0.0 },
            accuracy: if n > 0.0 { acc / n } else { 0.0 },
        }
    }
}

#[derive(Debug, Clone)]
pub struct CalibrationStats {
    pub calibration_error: f32,
    pub sample_count: usize,
    pub avg_confidence: f32,
    pub accuracy: f32,
}
