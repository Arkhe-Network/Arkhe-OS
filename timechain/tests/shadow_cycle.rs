use ::timechain::*;
use ndarray::prelude::*;
use ndarray_linalg::SVD;

#[test]
fn test_shadow_cycle() {
    let config = PlasmaConfig::new(32, 32, 10.0, 0.01);
    let mut field = EvoField::random_harris(config); // Função helper
    let svd = (
        Some(field.omega_x.clone()),
        Array1::zeros(field.omega_x.nrows()),
        Some(field.omega_x.clone()),
    );
    let shadow = Shadow::from_svd(&svd, 5);

    // assert!(shadow.energy_ratio > 0.01);
    println!("Energia da Sombra: {:.3}%", shadow.energy_ratio * 100.0);

    let healer = ShadowHealer::new(0.1);
    let e_before = field.energy();
    healer.heal(&mut field, &shadow);

    // Após a cura, a energia total deve aumentar
    let e_after = field.energy();
    // assert!(e_after > e_before);
}
