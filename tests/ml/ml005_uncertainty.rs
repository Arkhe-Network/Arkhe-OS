//! ARKHE — Teste de Invariante ML-005
//! "Quantificação de Incerteza em Surrogates Físicos"
//!
//! Verifica se modelos surrogate reportam incerteza calibrada.

use arkhe_materials::ml::surrogate::{SurrogateModel, UncertaintyMethod};
use arkhe_materials::ml::metrics::{expected_calibration_error, coverage_probability};

const MAX_ECE: f64 = 0.05; // Expected Calibration Error < 5%
const MIN_COVERAGE: f64 = 0.90; // 90% coverage for 95% CI

#[test]
fn ml005_uncertainty_reported() {
    let model = SurrogateModel::load("dft_surrogate.pt");

    // Verificar se modelo reporta incerteza
    let supports_uncertainty = model.uncertainty_method().is_some();
    assert!(
        supports_uncertainty,
        "ML-005 VIOLADO: Modelo surrogate não reporta incerteza.          Métodos suportados: GaussianProcess, MC Dropout, Deep Ensemble, BNN.          Nenhum método detectado."
    );
}

#[test]
fn ml005_calibration_error() {
    let model = SurrogateModel::load("dft_surrogate.pt");
    let test_set = load_dft_test_set();

    let mut predictions = Vec::new();
    let mut uncertainties = Vec::new();
    let mut ground_truths = Vec::new();

    for sample in test_set {
        let pred = model.predict_with_uncertainty(&sample.features);
        predictions.push(pred.mean);
        uncertainties.push(pred.std);
        ground_truths.push(sample.target);
    }

    let ece = expected_calibration_error(&predictions, &uncertainties, &ground_truths);
    assert!(
        ece < MAX_ECE,
        "ML-005 VIOLADO: Expected Calibration Error ({:.4}) excede limiar ({:.4}).          Incerteza não está calibrada. Ajustar método de quantificação.",
        ece, MAX_ECE
    );
}

#[test]
fn ml005_out_of_domain_detection() {
    let model = SurrogateModel::load("dft_surrogate.pt");

    // Dados dentro do domínio de treinamento
    let in_domain = load_in_domain_samples();
    // Dados fora do domínio (composições nunca vistas)
    let out_domain = load_out_of_domain_samples();

    let mean_uncertainty_in = in_domain.iter()
        .map(|s| model.predict_with_uncertainty(&s.features).std)
        .sum::<f64>() / in_domain.len() as f64;

    let mean_uncertainty_out = out_domain.iter()
        .map(|s| model.predict_with_uncertainty(&s.features).std)
        .sum::<f64>() / out_domain.len() as f64;

    assert!(
        mean_uncertainty_out > 3.0 * mean_uncertainty_in,
        "ML-005 VIOLADO: Incerteza fora do domínio ({:.4}) não é > 3×          incerteza no domínio ({:.4}). Modelo não detecta regiões de          alta incerteza epistêmica.",
        mean_uncertainty_out, mean_uncertainty_in
    );
}