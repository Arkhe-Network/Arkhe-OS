// circuits/governance.cairo — Programa Cairo para prova STARK
// Baseado em: Cairo circuits para verificação de governança

use core::array::ArrayTrait;
use core::felt252;
use core::traits::Into;

#[derive(Copy, Drop, Serde)]
struct GovernanceInputs {
    phi_values: Array<felt252>,  // Scores de coerência
    weights: Array<felt252>,     // Pesos dos agentes
    threshold: felt252,          // Threshold (85% = 85)
}

#[derive(Copy, Drop, Serde)]
struct GovernanceOutputs {
    weighted_phi: felt252,       // Média ponderada * 100
    consensus_reached: felt252,  // 1 se >= threshold
}

fn compute_weighted_phi(inputs: GovernanceInputs) -> GovernanceOutputs {
    let mut sum_phi = 0;
    let mut sum_w = 0;
    let mut i = 0;

    loop {
        if i >= inputs.phi_values.len() {
            break;
        }
        let phi = *inputs.phi_values.at(i);
        let w = *inputs.weights.at(i);
        sum_phi += phi * w;
        sum_w += w;
        i += 1;
    };

    // Evita divisão por zero
    if sum_w == 0 {
        return GovernanceOutputs {
            weighted_phi: 0,
            consensus_reached: 0,
        };
    }

    // Média ponderada: (sum_phi / sum_w) * 100
    let weighted_phi = (sum_phi * 100) / sum_w;
    let consensus_reached = if weighted_phi >= inputs.threshold { 1 } else { 0 };

    GovernanceOutputs {
        weighted_phi: weighted_phi,
        consensus_reached: consensus_reached,
    }
}

#[test]
fn test_governance() {
    let mut phi_values = ArrayTrait::new();
    phi_values.append(90);
    phi_values.append(85);
    phi_values.append(78);

    let mut weights = ArrayTrait::new();
    weights.append(3);
    weights.append(2);
    weights.append(1);

    let inputs = GovernanceInputs {
        phi_values: phi_values,
        weights: weights,
        threshold: 85,
    };

    let outputs = compute_weighted_phi(inputs);
    assert(outputs.weighted_phi == 86, 'weighted_phi should be 86');
    assert(outputs.consensus_reached == 1, 'consensus should be reached');
}