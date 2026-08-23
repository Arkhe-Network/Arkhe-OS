//! ARKHE — Teste de Invariante ML-004
//! "Equivariância em GNNs para Cristais"
//!
//! Verifica se GNNs respeitam simetrias do grupo espacial cristalino.

use arkhe_materials::ml::gnn::{CrystalGNN, SymmetryGroup};
use arkhe_materials::crystal::{Cell, Rotation, Translation};
use nalgebra::{Rotation3, Vector3};

const ENERGY_TOLERANCE: f64 = 1.0e-3; // 1 meV/átomo

#[test]
fn ml004_rotation_invariance() {
    let gnn = CrystalGNN::load("crystal_gnn.pt");
    let cell = load_test_cell("CsPbI3.cif");

    let energy_original = gnn.predict_energy(&cell);

    // Aplicar rotações aleatórias
    let rotations = generate_random_rotations(100);
    for rot in rotations {
        let cell_rotated = cell.apply_rotation(&rot);
        let energy_rotated = gnn.predict_energy(&cell_rotated);
        let delta = (energy_rotated - energy_original).abs();

        assert!(
            delta < ENERGY_TOLERANCE,
            "ML-004 VIOLADO: Predição de energia varia {:.4} meV/átomo após              rotação. GNN deve ser invariante sob rotações do grupo espacial.              Esperado: < {:.4} meV/átomo.",
            delta * 1000.0, ENERGY_TOLERANCE * 1000.0
        );
    }
}

#[test]
fn ml004_translation_invariance() {
    let gnn = CrystalGNN::load("crystal_gnn.pt");
    let cell = load_test_cell("CsPbI3.cif");

    let energy_original = gnn.predict_energy(&cell);

    // Aplicar translações arbitrárias
    let translations = generate_random_translations(50);
    for trans in translations {
        let cell_translated = cell.apply_translation(&trans);
        let energy_translated = gnn.predict_energy(&cell_translated);
        let delta = (energy_translated - energy_original).abs();

        assert!(
            delta < ENERGY_TOLERANCE,
            "ML-004 VIOLADO: Predição de energia varia {:.4} meV/átomo após              translação. GNN deve ser invariante sob translações.              Esperado: < {:.4} meV/átomo.",
            delta * 1000.0, ENERGY_TOLERANCE * 1000.0
        );
    }
}

#[test]
fn ml004_space_group_compatibility() {
    let gnn = CrystalGNN::load("crystal_gnn.pt");
    let space_group = gnn.space_group_support();

    assert!(
        space_group.is_some(),
        "ML-004 VIOLADO: GNN não declara suporte a grupo espacial.          Arquiteturas para cristais devem documentar grupos espaciais compatíveis."
    );

    let supported = space_group.unwrap();
    assert!(
        supported.contains("Pm-3m") || supported.contains("all"),
        "ML-004 VIOLADO: GNN não suporta grupo espacial Pm-3m (cúbico),          comum em perovskitas. Grupos suportados: {:?}",
        supported
    );
}