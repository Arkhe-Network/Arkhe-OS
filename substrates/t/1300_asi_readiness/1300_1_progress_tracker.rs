// ═══════════════════════════════════════════════════════════════════
// progress_tracker.rs — Substrato 1300.1.1: Complete Implementation
// Selo: CATHEDRAL-1300.1.1-PROGRESS-v1.0.0-2026-06-13
// Arquiteto: ORCID 0009-0005-2697-4668
// ═══════════════════════════════════════════════════════════════════

use std::collections::BTreeMap;
use chrono::{DateTime, Utc, Duration};
use serde::{Serialize, Deserialize};

// =============================================================================
// Core Types
// =============================================================================

/// A single benchmark measurement at a point in time.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityBenchmark {
    pub timestamp: DateTime<Utc>,
    pub benchmark_id: String,
    pub domain: String,
    pub metric_name: String,
    pub metric_value: f64,
    pub effective_compute_flops: f64,
    pub model_version: String,
    pub metadata: BTreeMap<String, String>,
}

impl CapabilityBenchmark {
    /// Convenience constructor
    pub fn new(
        benchmark_id: &str,
        domain: &str,
        metric_name: &str,
        metric_value: f64,
        compute_flops: f64,
    ) -> Self {
        Self {
            timestamp: Utc::now(),
            benchmark_id: benchmark_id.to_string(),
            domain: domain.to_string(),
            metric_name: metric_name.to_string(),
            metric_value,
            effective_compute_flops: compute_flops,
            model_version: String::new(),
            metadata: BTreeMap::new(),
        }
    }

    /// With optional metadata
    pub fn with_metadata(mut self, key: &str, value: &str) -> Self {
        self.metadata.insert(key.to_string(), value.to_string());
        self
    }
}

/// Estimation method used.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EstimationMethod {
    /// OLS linear regression on log(capability) vs log(compute)
    LogLinearCompute,
    /// Exponential fit: capability(t) = A * exp(λt)
    ExponentialTime,
    /// OLS linear regression on log(capability) vs time
    LogLinearTime,
    /// Rolling median growth rate
    RollingMedian,
    /// Ensemble of all valid methods
    Ensemble,
    /// No data / placeholder
    None,
}

/// Growth rate estimate from one or more methods.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GrowthRateEstimate {
    /// Year-over-year multiplicative growth rate (e.g., 2.5 = 150% growth)
    pub capability_growth_rate: f64,

    /// Year-over-year growth rate for effective compute
    pub effective_compute_rate: f64,

    /// Year-over-year algorithmic efficiency improvement rate
    pub algorithmic_efficiency_rate: f64,

    /// Estimated uncertainty (std dev of ensemble)
    pub uncertainty: f64,

    /// Method used
    pub method: EstimationMethod,

    /// Number of data points
    pub data_points: usize,

    /// Time range of data in days
    pub time_range_days: f64,

    /// Compute elasticity: d(log cap)/d(log compute)
    pub compute_elasticity: f64,

    /// R² of the fit (0.0 to 1.0, -1.0 if invalid)
    pub r_squared: f64,
}

impl Default for GrowthRateEstimate {
    fn default() -> Self {
        Self {
            capability_growth_rate: 0.0,
            effective_compute_rate: 0.0,
            algorithmic_efficiency_rate: 0.0,
            uncertainty: f64::NAN,
            method: EstimationMethod::None,
            data_points: 0,
            time_range_days: 0.0,
            compute_elasticity: f64::NAN,
            r_squared: -1.0,
        }
    }
}

impl GrowthRateEstimate {
    /// Create from a single growth rate (simple estimate)
    pub fn from_rate(rate: f64, method: EstimationMethod, points: usize) -> Self {
        Self {
            capability_growth_rate: rate,
            method,
            data_points: points,
            ..Default::default()
        }
    }

    /// Is this a valid (non-placeholder) estimate?
    pub fn is_valid(&self) -> bool {
        self.method != EstimationMethod::None
            && self.data_points >= 3
            && !self.capability_growth_rate.is_nan()
            && self.capability_growth_rate.is_finite()
    }

    /// Human-readable summary
    pub fn summary(&self) -> String {
        if !self.is_valid() {
            return "No valid estimate yet (need ≥3 data points)".to_string();
        }
        format!(
            "Growth: {:.2}×/yr (±{:.2}) [{} via {} points, R²={:.3}, range={:.0}d, elasticity={:.3}]",
            self.capability_growth_rate,
            self.uncertainty,
            self.effective_compute_rate,
            self.method_str(),
            self.data_points,
            self.r_squared,
            self.time_range_days,
            self.compute_elasticity,
        )
    }

    fn method_str(&self) -> &'static str {
        match self.method {
            EstimationMethod::LogLinearCompute => "log-lin(compute)",
            EstimationMethod::ExponentialTime => "exp(time)",
            EstimationMethod::LogLinearTime => "log-lin(time)",
            EstimationMethod::RollingMedian => "rolling-median",
            EstimationMethod::Ensemble => "ensemble",
            EstimationMethod::None => "none",
        }
    }

    /// Convert growth rate to "X×/yr" string
    pub fn rate_str(&self) -> String {
        if !self.is_valid() {
            return "N/A".to_string();
        }
        format!("{:.2}×/yr", self.capability_growth_rate)
    }

    /// Is growth super-exponential? (rate > 10×/yr)
    pub fn is_super_exponential(&self) -> bool {
        self.is_valid() && self.capability_growth_rate > 10.0
    }

    /// Is growth plateauing? (rate < 1.05×/yr)
    pub fn is_plateauing(&self) -> bool {
        self.is_valid() && self.capability_growth_rate < 1.05 && self.capability_growth_rate > 0.0
    }

    /// Is growth negative? (declining capabilities)
    pub fn is_declining(&self) -> bool {
        self.is_valid() && self.capability_growth_rate < 0.0
    }
}

// =============================================================================
// OLS Regression Helper
// =============================================================================

/// Ordinary Least Squares linear regression: y = α + βx
struct OLSResult {
    slope: f64,
    intercept: f64,
    r_squared: f64,
    n: usize,
}

fn ols_regression(xs: &[f64], ys: &[f64]) -> OLSResult {
    let n = xs.len().max(ys.len());
    if n < 3 {
        return OLSResult { slope: 0.0, intercept: 0.0, r_squared: -1.0, n };
    }

    let n_f = n as f64;
    let sum_x: f64 = xs.iter().copied().sum();
    let sum_y: f64 = ys.iter().copied().sum();
    let sum_xx: f64 = xs.iter().map(|x| x * x).sum();
    let sum_xy: f64 = xs.iter().zip(ys.iter()).map(|(x, y)| x * y).sum();
    let sum_yy: f64 = ys.iter().map(|y| y * y).sum();

    let denom = n_f * sum_xx - sum_x * sum_x;
    if denom.abs() < 1e-12 {
        return OLSResult { slope: 0.0, intercept: sum_y / n_f, r_squared: -1.0, n };
    }

    let slope = (n_f * sum_xy - sum_x * sum_y) / denom;
    let intercept = (sum_y - slope * sum_x) / n_f;

    // R² = 1 - SS_res / SS_tot
    let mean_y = sum_y / n_f;
    let ss_tot: f64 = ys.iter().map(|y| (y - mean_y).powi(2)).sum();
    let ss_res: f64 = xs.iter().zip(ys.iter())
        .map(|(x, y)| {
            let predicted = intercept + slope * x;
            (y - predicted).powi(2)
        })
        .sum();

    let r_squared = if ss_tot > 1e-12 {
        1.0 - ss_res / ss_tot
    } else {
        -1.0
    };

    OLSResult { slope, intercept, r_squared, n }
}

// =============================================================================
// Regression Methods
// =============================================================================

/// Log-linear regression: log(capability) = α + β * log(compute)
fn log_linear_compute_regression(
    data: &[CapabilityBenchmark],
) -> GrowthRateEstimate {
    let points: Vec<(f64, f64)> = data
        .iter()
        .filter(|b| b.metric_value > 0.0 && b.effective_compute_flops > 0.0)
        .map(|b| (b.effective_compute_flops.ln(), b.metric_value.ln()))
        .collect();

    if points.len() < 3 {
        return GrowthRateEstimate::default();
    }

    let ols = ols_regression(
        &points.iter().map(|(x, _)| *x).collect::<Vec<_>>(),
        &points.iter().map(|(_, y)| *y).collect::<Vec<_>>(),
    );

    // β = d(log cap)/d(log compute) = compute elasticity
    // growth_rate ≈ β × compute_growth_rate
    // For now, return elasticity (compute growth needs to be passed in separately)

    GrowthRateEstimate {
        compute_elasticity: ols.slope,
        r_squared: ols.r_squared,
        method: EstimationMethod::LogLinearCompute,
        data_points: ols.n,
        ..Default::default()
    }
}

/// Exponential fit: log(capability) = α + λ * time
fn exponential_time_regression(
    data: &[CapabilityBenchmark],
) -> GrowthRateEstimate {
    let points: Vec<(f64, f64)> = data
        .iter()
        .filter(|b| b.metric_value > 0.0)
        .map(|b| {
            let days = (b.timestamp - data.first().map(|f| f.timestamp).unwrap_or(b.timestamp))
                .num_days()
                .max(1) as f64;
            (days, b.metric_value.ln())
        })
        .collect();

    if points.len() < 3 {
        return GrowthRateEstimate::default();
    }

    let ols = ols_regression(
        &points.iter().map(|(x, _)| *x).collect::<Vec<_>>(),
        &points.iter().map(|(_, y)| *y).collect::<Vec<_>>(),
    );

    // λ = d(log cap)/dt (in days)
    // Annual growth rate = exp(λ × 365.25) - 1
    let annual_rate = (ols.slope * 365.25).exp() - 1.0;

    GrowthRateEstimate {
        capability_growth_rate: annual_rate,
        r_squared: ols.r_squared,
        method: EstimationMethod::ExponentialTime,
        data_points: ols.n,
        ..Default::default()
    }
}

/// Log-linear time regression: log(capability) = α + β * time
fn log_linear_time_regression(
    data: &[CapabilityBenchmark],
) -> GrowthRateEstimate {
    let points: Vec<(f64, f64)> = data
        .iter()
        .filter(|b| b.metric_value > 0.0)
        .map(|b| {
            let days = (b.timestamp - data.first().map(|f| f.timestamp).unwrap_or(b.timestamp))
                .num_days()
                .max(1) as f64;
            (days, b.metric_value.ln())
        })
        .collect();

    if points.len() < 3 {
        return GrowthRateEstimate::default();
    }

    let ols = ols_regression(
        &points.iter().map(|(x, _)| *x).collect::<Vec<_>>(),
        &points.iter().map(|(_, y)| *y).collect::<Vec<_>>(),
    );

    let annual_rate = (ols.slope * 365.25).exp() - 1.0;

    GrowthRateEstimate {
        capability_growth_rate: annual_rate,
        r_squared: ols.r_squared,
        method: EstimationMethod::LogLinearTime,
        data_points: ols.n,
        ..Default::default()
    }
}

/// Rolling median growth rate
fn rolling_median_regression(
    data: &[CapabilityBenchmark],
    window_size: usize,
) -> GrowthRateEstimate {
    let values: Vec<f64> = data
        .iter()
        .filter(|b| b.metric_value > 0.0)
        .map(|b| b.metric_value)
        .collect();

    if values.len() < window_size * 2 {
        return GrowthRateEstimate::default();
    }

    // Compute rolling growth rates (pairwise ratio over window)
    let mut growth_rates = Vec::new();
    for i in window_size..values.len() {
        let past: f64 = values[i - window_size..i].iter().sum::<f64>() / window_size as f64;
        let recent: f64 = values[i - window_size + 1..=i].iter().sum::<f64>() / window_size as f64;
        if past > 0.0 {
            growth_rates.push(recent / past);
        }
    }

    if growth_rates.is_empty() {
        return GrowthRateEstimate::default();
    }

    // Median growth rate → annual
    growth_rates.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let median = growth_rates[growth_rates.len() / 2];
    let annual = median.powi(365.25 as i32) - 1.0;

    // Uncertainty: IQR of growth rates
    let q1 = growth_rates[growth_rates.len() / 4];
    let q3 = growth_rates[growth_rates.len() * 3 / 4];
    let iqr = q3 - q1;
    let uncertainty = iqr / 2.0 / 365.25; // Approximate annual uncertainty

    GrowthRateEstimate {
        capability_growth_rate: annual,
        uncertainty,
        method: EstimationMethod::RollingMedian,
        data_points: growth_rates.len(),
        ..Default::default()
    }
}

// =============================================================================
// ProgressTracker
// =============================================================================

/// Tracks AI progress across benchmarks and estimates growth rates.
pub struct ProgressTracker {
    history: Vec<CapabilityBenchmark>,
    estimates: Vec<GrowthRateEstimate>,
    window_size: usize,
    compute_history: Vec<(DateTime<Utc>, f64)>,
}

impl ProgressTracker {
    /// Create tracker with specified rolling window (in days)
    pub fn new(window_days: f64) -> Self {
        Self {
            history: Vec::new(),
            estimates: Vec::new(),
            window_size: (window_days * 10.0) as usize, // Approximate data points per window
            compute_history: Vec::new(),
        }
    }

    /// Record a benchmark measurement
    pub fn record(&mut self, benchmark: CapabilityBenchmark) {
        if benchmark.effective_compute_flops > 0.0 {
            self.compute_history.push((
                benchmark.timestamp,
                benchmark.effective_compute_flops,
            ));
        }
        self.history.push(benchmark);
        self.recompute_estimates();
    }

    /// Recompute all growth rate estimates using ensemble
    pub fn recompute_estimates(&mut self) {
        self.estimates = vec![
            log_linear_compute_regression(&self.history),
            exponential_time_regression(&self.history),
            log_linear_time_regression(&self.history),
            rolling_median_regression(&self.history, self.window_size),
        ];

        // Ensemble: average of valid estimates
        let valid: Vec<&GrowthRateEstimate> = self.estimates
            .iter()
            .filter(|e| e.is_valid())
            .collect();

        if valid.len() < 2 {
            return;
        }

        let mean_rate: f64 = valid.iter()
            .map(|e| e.capability_growth_rate)
            .sum::<f64>() / valid.len() as f64;

        let std_dev: f64 = valid.iter()
            .map(|e| (e.capability_growth_rate - mean_rate).powi(2))
            .sum::<f64>() / valid.len() as f64;
        let std_dev = std_dev.sqrt();

        // Compute compute and efficiency growth rates
        let compute_rate = self.estimate_compute_growth_rate();
        let algo_eff_rate = self.estimate_algo_efficiency_growth();

        // Create ensemble estimate
        let ensemble = GrowthRateEstimate {
            capability_growth_rate: mean_rate,
            uncertainty: std_dev,
            effective_compute_rate: compute_rate,
            algorithmic_efficiency_rate: algo_eff_rate,
            method: EstimationMethod::Ensemble,
            data_points: valid.iter().map(|e| e.data_points).max().unwrap_or(0),
            time_range_days: self.compute_time_range(),
            r_squared: valid.iter()
                .map(|e| if e.r_squared > 0.0 { e.r_squared } else { 0.0 })
                .sum::<f64>() / valid.len() as f64,
            compute_elasticity: valid.iter()
                .map(|e| {
                    if e.compute_elasticity.is_nan() { 0.5 }
                    else { e.compute_elasticity }
                })
                .sum::<f64>() / valid.len() as f64,
        };

        self.estimates.push(ensemble);
    }

    /// Get latest ensemble estimate
    pub fn latest_estimate(&self) -> Option<&GrowthRateEstimate> {
        self.estimates.iter().rev().find(|e| e.method == EstimationMethod::Ensemble)
    }

    /// Get latest estimate of any method
    pub fn latest_any_estimate(&self) -> Option<&GrowthRateEstimate> {
        self.estimates.last().filter(|e| e.is_valid())
    }

    /// Get all estimates
    pub fn all_estimates(&self) -> &[GrowthRateEstimate] {
        &self.estimates
    }

    /// Get all benchmarks
    pub fn history(&self) -> &[CapabilityBenchmark] {
        &self.history
    }

    /// Check if growth is super-exponential (rate > 10×/yr)
    pub fn is_super_exponential(&self) -> bool {
        self.latest_estimate()
            .map(|e| e.is_super_exponential())
            .unwrap_or(false)
    }

    /// Check if growth is plateauing
    pub fn is_plateauing(&self) -> bool {
        self.latest_estimate()
            .map(|e| e.is_plateauing())
            .unwrap_or(false)
    }

    /// Rough time to ASI (very approximate!)
    pub fn time_to_asi(
        &self,
        agi_level: f64,
        asi_level: f64,
    ) -> Option<f64> {
        let est = self.latest_estimate()?;
        let rate = est.capability_growth_rate;
        if rate <= 1.0 {
            return None; // Not growing
        }

        if agi_level >= asi_level {
            return Some(0.0); // Already at or above ASI
        }

        // log(ASI/AGI) / log(1 + rate) = years
        let log_ratio = (asi_level.ln() / agi_level.ln()).max(0.0);
        let log_growth = (1.0 + rate).ln();
        let years = log_ratio / log_growth;

        Some(years)
    }

    // =================================================================
    // Private helpers
    // =================================================================

    fn estimate_compute_growth_rate(&self) -> f64 {
        let pairs: Vec<(f64, f64)> = self.compute_history
            .windows(2)
            .filter_map(|w| {
                let (t1, c1) = w[0];
                let (t2, c2) = w[1];
                let dt_days = (t2 - t1).num_days();
                if dt_days > 0 && c1 > 0.0 && c2 > 0.0 {
                    Some((dt_days as f64, (c2 / c1).ln()))
                } else {
                    None
                }
            })
            .collect();

        if pairs.len() < 3 { return 1.0; }

        let ols = ols_regression(
            &pairs.iter().map(|(x, _)| *x).collect::<Vec<_>>(),
            &pairs.iter().map(|(_, y)| *y).collect::<Vec<_>>(),
        );

        (ols.slope * 365.25).exp()
    }

    fn estimate_algo_efficiency_growth(&self) -> f64 {
        let points: Vec<(f64, f64)> = self.history
            .iter()
            .filter(|b| b.metric_value > 0.0 && b.effective_compute_flops > 0.0)
            .map(|b| (b.effective_compute_flops.ln(), b.metric_value.ln()))
            .collect();

        if points.len() < 3 { return 1.0; }

        // Algo efficiency = capability / compute
        // Growth of algo efficiency = how fast this ratio improves
        let ratios: Vec<(f64, f64)> = self.history
            .windows(2)
            .filter_map(|w| {
                let (t1, c1, r1) = (w[0].timestamp, w[0].effective_compute_flops, w[0].metric_value);
                let (t2, c2, r2) = (w[1].timestamp, w[1].effective_compute_flops, w[1].metric_value);
                let dt_days = (t2 - t1).num_days();
                if dt_days > 0 && c1 > 0.0 && r1 > 0.0 && r2 > 0.0 {
                    let ratio2 = (r2 / c2) / (r1 / c1);
                    Some((dt_days as f64, ratio2.ln()))
                } else {
                    None
                }
            })
            .collect();

        if ratios.len() < 3 { return 1.0; }

        let ols = ols_regression(
            &ratios.iter().map(|(x, _)| *x).collect::<Vec<_>>(),
            &ratios.iter().map(|(_, y)| *y).collect::<Vec<_>>(),
        );

        (ols.slope * 365.25).exp()
    }

    fn compute_time_range(&self) -> f64 {
        if self.history.len() < 2 { return 0.0; }
        (self.history.last().unwrap().timestamp - self.history.first().unwrap().timestamp)
            .num_days() as f64
    }
}
