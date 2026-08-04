use floquet_ptc::{ExceptionalPointResult, FloquetHamiltonian, PTCSignature};

#[test]
fn test_transitions() {
    let hamiltonian = FloquetHamiltonian {
        omega_0: 100.0,
        omega_d: 10.0,
        eta_0: 0.05, // Below the 0.1 threshold to induce a divergence of zero
        gamma_0: 0.5,
    };

    // With eta_0 = 0.05, the effective mass modulation |eta| <= 0.05 < 0.1,
    // so delta_gamma = 0, meaning divergence = 0. Coalesced.
    let result = ExceptionalPointResult::analyze(&hamiltonian, 0.0);
    assert_eq!(result.signature, PTCSignature::Coalesced);

    // Now push eta_0 above 0.1 to induce divergence and PTC regime
    let hamiltonian = FloquetHamiltonian {
        eta_0: 0.8,
        ..hamiltonian
    };

    let result = ExceptionalPointResult::analyze(&hamiltonian, 0.0);
    assert_eq!(result.signature, PTCSignature::BrokenSymmetryGain);
}
