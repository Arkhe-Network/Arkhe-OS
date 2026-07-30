use aegis_plausible_reasoner::{
    ContextEmbedding, PlausibleReasoner, Policy, PolicyRule, Condition, PolicyAction, PolicyMutation,
};

fn main() {
    let mut reasoner = PlausibleReasoner::new();
    let mut policy = Policy::default();

    // Simulated context: high interference, low acceptance for DeFi recommendations
    let ctx = ContextEmbedding {
        calibration_error: 0.35,
        avg_interference: 0.72,
        acceptance_rate: 0.45,
        proof_latency_ms: 180.0,
        memory_proof_usage_rate: 0.2,
        high_risk_action_rate: 0.6,
        recent_audit_flags: 1,
        stagnation_rounds: 2,
    };

    // Generate mutation proposals
    let mutations = reasoner.propose_structural_edits(&ctx, &policy, true);

    // Example mutations that AEGIS might generate:
    let example_mutations = vec![
        PolicyMutation::AddRule(PolicyRule {
            id: 100,
            condition: Condition::And(
                Box::new(Condition::ActionRisk("high".to_string())),
                Box::new(Condition::HubName("defi-yield".to_string())),
            ),
            action: PolicyAction::CommitMemoryOnly,
            priority: 50,
        }),
        PolicyMutation::ModifyRule {
            rule_id: 42,
            new_condition: Condition::MemoryCommitmentStale(5),
            new_action: PolicyAction::ProveAndVerifyOnChain,
        },
        PolicyMutation::AddRule(PolicyRule {
            id: 101,
            condition: Condition::InterferenceAbove(0.65),
            action: PolicyAction::AdjustThreshold {
                field: "min_recommendation_value_usd".to_string(),
                value: 5.0,
            },
            priority: 80,
        }),
    ];

    println!("Proposed mutations by PlausibleReasoner:");
    for m in mutations {
        println!("  {:?}", m);
    }

    println!("\nExample policy mutations for PicoAds hubs:");
    for m in example_mutations {
        println!("  {:?}", m);
    }
}
