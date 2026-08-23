//! ARKHE — Teste de Invariante ML-003
//! "Precisão Numérica em Simulações Quânticas"
//!
//! Verifica se modelos de simulação quântica usam float64
//! quando a escala de energia exige precisão < 1 meV.

use arkhe_qed::ml::quantum_model::QuantumSurrogate;
use arkhe_qed::units::{eV, Hartree, meV};

const ENERGY_TOLERANCE: f64 = 1.0 * meV; // 1 meV

#[test]
fn ml003_float64_for_atomic_energies() {
    let model = QuantumSurrogate::load("qed_surrogate.pt");

    // Verificar dtype dos parâmetros do modelo
    let dtypes = model.parameter_dtypes();
    let all_float64 = dtypes.iter().all(|dt| dt == "float64");

    assert!(
        all_float64,
        "ML-003 VIOLADO: Modelo quântico usa precisão inferior a float64.          Dtypes encontrados: {:?}. Energias atômicas requerem float64          para erros < 1 meV.",
        dtypes
    );
}

#[test]
fn ml003_convergence_tolerance() {
    let model = QuantumSurrogate::load("qed_surrogate.pt");
    let test_systems = load_test_systems("qed_test_set.json");

    for system in test_systems {
        let energy_ml = model.predict_energy(&system);
        let energy_dft = system.reference_energy; // Ground truth DFT

        let error = (energy_ml - energy_dft).abs();
        assert!(
            error < ENERGY_TOLERANCE,
            "ML-003 VIOLADO: Erro de predição ({:.4} meV) excede tolerância              ({:.4} meV) para sistema {}. Verificar precisão numérica.",
            error / meV, ENERGY_TOLERANCE / meV, system.id
        );
    }
}

#[test]
fn ml003_precision_documented() {
    let doc_path = std::path::Path::new("docs/qed/numerical_precision.md");
    assert!(
        doc_path.exists(),
        "ML-003 VIOLADO: Documentação de precisão numérica não encontrada.          Criar docs/qed/numerical_precision.md justificando a escolha de dtype."
    );

    let content = std::fs::read_to_string(doc_path).unwrap();
    assert!(
        content.contains("float64") || content.contains("tf.float64") || content.contains("torch.float64"),
        "ML-003 VIOLADO: Documentação não menciona float64 como precisão padrão."
    );
}