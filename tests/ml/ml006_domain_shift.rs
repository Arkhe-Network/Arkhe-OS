//! ARKHE — Teste de Invariante ML-006
//! "Validação de Distribuição em Transfer Learning"
//!
//! Verifica se transfer learning entre domínios de materiais
//! é precedido por validação estatística de similaridade.

use arkhe_materials::ml::transfer::{DomainAdapter, DistributionTest};
use arkhe_materials::ml::metrics::maximum_mean_discrepancy;

const MMD_THRESHOLD: f64 = 0.5; // MMD normalizado

#[test]
fn ml006_distribution_similarity() {
    let source_domain = load_domain("perovskite_halide");
    let target_domain = load_domain("perovskite_oxide");

    // Calcular MMD entre embeddings dos domínios
    let mmd = maximum_mean_discrepancy(
        &source_domain.embeddings(),
        &target_domain.embeddings()
    );

    println!("ML-006: MMD entre domínios = {:.4}", mmd);

    if mmd > MMD_THRESHOLD {
        // Se distribuições divergentes, exigir domain adaptation
        let adapter = DomainAdapter::coral()
            .fit(&source_domain, &target_domain);

        let mmd_adapted = maximum_mean_discrepancy(
            &adapter.transform_source(),
            &target_domain.embeddings()
        );

        assert!(
            mmd_adapted < MMD_THRESHOLD,
            "ML-006 VIOLADO: MMD após domain adaptation ({:.4}) ainda excede              limiar ({:.4}). Transfer learning não é viável entre esses domínios              sem coleta adicional de dados no domínio-alvo.",
            mmd_adapted, MMD_THRESHOLD
        );
    }
}

#[test]
fn ml006_ks_test_validation() {
    let source = load_domain("perovskite_halide").feature_distribution();
    let target = load_domain("perovskite_oxide").feature_distribution();

    let ks_statistic = kolmogorov_smirnov_test(&source, &target);
    let p_value = ks_p_value(ks_statistic, source.len(), target.len());

    assert!(
        p_value > 0.05,
        "ML-006 VIOLADO: Teste KS rejeita hipótese nula (p={:.4}).          Distribuições são significativamente diferentes.          Transfer learning direto proibido. MMD={:.4}",
        p_value,
        maximum_mean_discrepancy(&source, &target)
    );
}

#[test]
fn ml006_transfer_learning_documented() {
    let doc_path = std::path::Path::new("docs/ml/transfer_learning_approval.md");
    assert!(
        doc_path.exists(),
        "ML-006 VIOLADO: Documentação de aprovação de transfer learning não encontrada.          Criar docs/ml/transfer_learning_approval.md com:          (1) domínios fonte e alvo, (2) métricas de similaridade,          (3) método de adaptation (se aplicável), (4) aprovação do materials-scientist."
    );
}