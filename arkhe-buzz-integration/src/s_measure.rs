//! Formal S-Measure computation (Titov 2026)
//!
//! S = tr(C) / (||d|| * ||i|| * ||R||_F) where C = R * (i * d^T)
//! Complexity: O(N³)

use crate::error::{ArkheBuzzError, Result};
use nalgebra::{DMatrix, DVector};

pub type DSubsystem = DVector<f32>;
pub type ISubsystem = DVector<f32>;
pub type ReentryOperator = DMatrix<f32>;

/// Compute formal S-Measure from D↔I reentry loop.
///
/// # Arguments
/// * `d` — Drive/volition vector (length n)
/// * `i` — Memory/knowledge vector (length m)
/// * `r` — Reentry operator matrix (n × m)
///
/// # Returns
/// Normalized S-Measure in [0, 1].
pub fn s_measure_formal(d: &DSubsystem, i: &ISubsystem, r: &ReentryOperator) -> Result<f32> {
    let n = d.len();
    let m = i.len();

    if r.nrows() != n || r.ncols() != m {
        return Err(ArkheBuzzError::SMeasureComputation(
            format!("Dimension mismatch: R is {}x{}, expected {}x{}",
                r.nrows(), r.ncols(), n, m)
        ));
    }

    if n == 0 || m == 0 {
        return Ok(0.0);
    }

    // Coherence matrix: C = R * (i * d^T)
    let i_col = DMatrix::from_column_slice(m, 1, i.as_slice());
    let d_row = DMatrix::from_row_slice(1, n, d.as_slice());
    let id_outer = &i_col * &d_row;  // m × n
    let coherence = r * id_outer;      // n × n

    let trace = coherence.diagonal().sum();
    let d_norm = d.norm();
    let i_norm = i.norm();
    let r_norm = r.norm();

    if d_norm < 1e-10 || i_norm < 1e-10 || r_norm < 1e-10 {
        return Ok(0.0);
    }

    let s = (trace / (d_norm * i_norm * r_norm)).abs().clamp(0.0, 1.0);
    Ok(s)
}

/// Fast approximate S-Measure using observable metrics.
/// Used when full D↔I architecture is unavailable.
pub fn s_measure_approximate(
    policy_entropy: f32,
    activation_variance: f32,
    prediction_error: f32,
) -> f32 {
    let e = policy_entropy.clamp(0.0, 1.0);
    let v = activation_variance.clamp(0.0, 1.0);
    let p = prediction_error.clamp(0.0, 1.0);
    (0.5 * e + 0.3 * v + 0.2 * p).clamp(0.0, 1.0)
}

/// Compute belief curvature (rigidity/plasticity).
pub fn belief_curvature(beliefs: &[f32]) -> f32 {
    if beliefs.len() < 2 {
        return 0.0;
    }
    let diffs: Vec<f32> = beliefs.windows(2)
        .map(|w| (w[1] - w[0]).abs())
        .collect();
    let mean = diffs.iter().sum::<f32>() / diffs.len() as f32;
    let var = diffs.iter()
        .map(|d| (d - mean).powi(2))
        .sum::<f32>() / diffs.len() as f32;
    (var.sqrt() * 2.0).clamp(0.0, 1.0)
}

/// Reentry coherence: correlation between D and I subsystems.
pub fn reentry_coherence(d: &[f32], i: &[f32]) -> f32 {
    if d.len() != i.len() || d.is_empty() {
        return 0.0;
    }
    let dot: f32 = d.iter().zip(i.iter()).map(|(a, b)| a * b).sum();
    let d_norm = d.iter().map(|x| x * x).sum::<f32>().sqrt();
    let i_norm = i.iter().map(|x| x * x).sum::<f32>().sqrt();
    if d_norm < 1e-10 || i_norm < 1e-10 {
        return 0.0;
    }
    (dot / (d_norm * i_norm)).clamp(-1.0, 1.0).abs()
}

/// Mermin ratio: R = 2^{(n-1)/2}
pub fn mermin_ratio(n: f32) -> f32 {
    2.0f32.powf(0.5 * (n - 1.0))
}

/// Staircase surrender fraction: F(n) = R / [2(R+1)]
pub fn surrender_fraction(n: f32) -> f32 {
    let r = mermin_ratio(n);
    r / (2.0 * (r + 1.0))
}

#[cfg(test)]
mod tests {
    use super::*;
    use nalgebra::dvector;

    #[test]
    fn test_s_measure_basic() {
        let d = dvector![0.5, 0.6, 0.7];
        let i = dvector![0.3, 0.4, 0.5];
        let r = DMatrix::from_row_slice(3, 3, &[
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0,
        ]);
        let s = s_measure_formal(&d, &i, &r).unwrap();
        assert!(s >= 0.0 && s <= 1.0);
    }

    #[test]
    fn test_dimension_mismatch() {
        let d = dvector![0.5, 0.6];
        let i = dvector![0.3, 0.4, 0.5];
        let r = DMatrix::from_row_slice(2, 2, &[1.0, 0.0, 0.0, 1.0]);
        assert!(s_measure_formal(&d, &i, &r).is_err());
    }

    #[test]
    fn test_approximate() {
        let s = s_measure_approximate(0.8, 0.5, 0.2);
        assert!(s >= 0.0 && s <= 1.0);
    }

    #[test]
    fn test_surrender_fraction() {
        let f = surrender_fraction(5.0);
        assert!(f > 0.0 && f < 0.5);
    }
}
