//! ARKHE — Teste de Invariante ML-001
//! "Validação Contra Baseline Estatístico"
//!
//! Verifica se um modelo preditivo proposto supera um baseline
//! estatístico (Random Forest / XGBoost) em pelo menos 10%.

use arkhe_materials::ml::baseline::{BaselineModel, ModelComparison};
use arkhe_materials::ml::metrics::{r2_score, rmse, mae};

/// Threshold mínimo de melhoria sobre baseline (10%)
const BASELINE_IMPROVEMENT_THRESHOLD: f64 = 1.10;

#[test]
fn ml001_baseline_comparison_regression() {
    // Dataset sintético: propriedades de perovskitas
    let (X_train, y_train, X_test, y_test) = load_perovskite_dataset();

    // Baseline: Random Forest
    let baseline = BaselineModel::random_forest()
        .n_estimators(500)
        .max_depth(None)
        .train(&X_train, &y_train);

    let y_pred_baseline = baseline.predict(&X_test);
    let r2_baseline = r2_score(&y_test, &y_pred_baseline);
    let rmse_baseline = rmse(&y_test, &y_pred_baseline);

    // Modelo proposto (placeholder para GNN ou Transformer)
    let proposed = load_proposed_model("model_checkpoint.pt");
    let y_pred_proposed = proposed.predict(&X_test);
    let r2_proposed = r2_score(&y_test, &y_pred_proposed);
    let rmse_proposed = rmse(&y_test, &y_pred_proposed);

    // Verificar se modelo proposto supera baseline em >= 10%
    let r2_improvement = r2_proposed / r2_baseline;
    let rmse_improvement = rmse_baseline / rmse_proposed; // menor RMSE é melhor

    assert!(
        r2_improvement >= BASELINE_IMPROVEMENT_THRESHOLD ||
        rmse_improvement >= BASELINE_IMPROVEMENT_THRESHOLD,
        "ML-001 VIOLADO: Modelo proposto (R²={:.4}, RMSE={:.4}) não supera baseline          (R²={:.4}, RMSE={:.4}) em >= 10%. Melhoria R²={:.2}%, RMSE={:.2}%",
        r2_proposed, rmse_proposed, r2_baseline, rmse_baseline,
        (r2_improvement - 1.0) * 100.0,
        (rmse_improvement - 1.0) * 100.0
    );

    // Teste t de Student para significância estatística (p < 0.05)
    let p_value = paired_t_test(&y_test, &y_pred_baseline, &y_pred_proposed);
    assert!(
        p_value < 0.05,
        "ML-001 VIOLADO: Diferença não é estatisticamente significativa (p={:.4})",
        p_value
    );
}

#[test]
fn ml001_baseline_comparison_classification() {
    let (X_train, y_train, X_test, y_test) = load_stability_dataset();

    // Baseline: SVM
    let baseline = BaselineModel::svm()
        .kernel("rbf")
        .train(&X_train, &y_train);

    let y_pred_baseline = baseline.predict(&X_test);
    let f1_baseline = f1_score(&y_test, &y_pred_baseline);

    // Modelo proposto
    let proposed = load_proposed_model("classifier_checkpoint.pt");
    let y_pred_proposed = proposed.predict(&X_test);
    let f1_proposed = f1_score(&y_test, &y_pred_proposed);

    let f1_improvement = f1_proposed / f1_baseline;
    assert!(
        f1_improvement >= BASELINE_IMPROVEMENT_THRESHOLD,
        "ML-001 VIOLADO: Classificador proposto (F1={:.4}) não supera baseline          (F1={:.4}) em >= 10%. Melhoria={:.2}%",
        f1_proposed, f1_baseline, (f1_improvement - 1.0) * 100.0
    );
}