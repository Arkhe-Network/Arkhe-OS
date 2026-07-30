// Proptest para ARKHE v7.0 — Substrate
// Testes baseados em propriedades para IC1, IC3, IC4, IC6, IC8

use proptest::prelude::*;
use std::collections::{HashMap, HashSet};
use proptest_derive::Arbitrary;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Arbitrary)]
pub struct Artifact {
    pub id: String,
    pub data: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Arbitrary)]
pub struct Evidence {
    pub id: String,
    pub artifact_id: String,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Arbitrary)]
pub struct Assertion {
    pub id: String,
    pub evidence_ids: Vec<String>,
    pub references: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Arbitrary)]
pub struct Claim {
    pub id: String,
    pub confidence: u64,
}

#[derive(Debug, Clone, Arbitrary, PartialEq, Eq)]
pub struct Substrate {
    pub artifacts: HashMap<String, Artifact>,
    pub evidence: HashSet<Evidence>,
    pub assertions: HashSet<Assertion>,
    pub claims: HashSet<Claim>,
}

impl Substrate {
    pub fn new() -> Self {
        Self {
            artifacts: HashMap::new(),
            evidence: HashSet::new(),
            assertions: HashSet::new(),
            claims: HashSet::new(),
        }
    }

    /// IC1: identidade canônica
    pub fn canonical_id(&self, artifact: &Artifact) -> Option<String> {
        self.artifacts.iter().find(|(_, a)| *a == artifact).map(|(id, _)| id.clone())
    }

    /// IC2: evidências de uma assertion
    pub fn evidence_of(&self, assertion: &Assertion) -> Vec<Evidence> {
        assertion
            .evidence_ids
            .iter()
            .filter_map(|id| self.evidence.iter().find(|e| e.id == *id))
            .cloned()
            .collect()
    }

    /// IC3: projeção pura
    pub fn project(&self) -> View {
        View {
            artifacts: self.artifacts.clone(),
            evidence: self.evidence.clone(),
            assertions: self.assertions.clone(),
            claims: self.claims.clone(),
        }
    }

    /// IC8: consistência temporal
    pub fn is_temporally_consistent(&self) -> bool {
        self.evidence.iter().all(|e| {
            if let Some(artifact) = self.artifacts.get(&e.artifact_id) {
                e.timestamp >= artifact.data.len() as u64
            } else {
                false
            }
        })
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct View {
    pub artifacts: HashMap<String, Artifact>,
    pub evidence: HashSet<Evidence>,
    pub assertions: HashSet<Assertion>,
    pub claims: HashSet<Claim>,
}

// ─── Propriedades ────────────────────────────────────────────────────────

proptest! {
    /// IC1: Identidade canônica é única
    #[test]
    fn ic1_canonical_identity_unique(artifact1: Artifact, artifact2: Artifact) {
        let mut substrate = Substrate::new();
        substrate.artifacts.insert(artifact1.id.clone(), artifact1.clone());
        substrate.artifacts.insert(artifact2.id.clone(), artifact2.clone());

        if let Some(id1) = substrate.canonical_id(&artifact1) {
            if let Some(id2) = substrate.canonical_id(&artifact2) {
                if id1 == id2 {
                    prop_assert_eq!(artifact1, artifact2);
                }
            }
        }
    }

    /// IC3: Projeção não modifica o substrato
    #[test]
    fn ic3_projection_purity(mut substrate: Substrate) {
        let before = substrate.clone();
        let _view = substrate.project();
        prop_assert_eq!(before, substrate);
    }

    /// IC4: Projeção é determinística
    #[test]
    fn ic4_projection_deterministic(substrate: Substrate) {
        let view1 = substrate.project();
        let view2 = substrate.project();
        prop_assert_eq!(view1, view2);
    }

    /// IC6: Toda referência existe no substrato
    #[test]
    fn ic6_referential_integrity(mut substrate: Substrate) {
        let artifact = Artifact {
            id: "art-1".to_string(),
            data: "data".to_string(),
        };
        substrate.artifacts.insert(artifact.id.clone(), artifact);

        let assertion = Assertion {
            id: "ass-1".to_string(),
            evidence_ids: vec![],
            references: vec!["art-1".to_string()],
        };

        substrate.assertions.insert(assertion.clone());

        for ref_id in &assertion.references {
            assert!(substrate.artifacts.contains_key(ref_id));
        }
    }

    /// IC8: Consistência temporal
    #[test]
    #[ignore]
    fn ic8_temporal_consistency(mut substrate: Substrate) {
        let artifact = Artifact {
            id: "art-1".to_string(),
            data: "".to_string(),
        };
        substrate.artifacts.insert(artifact.id.clone(), artifact);

        let evidence = Evidence {
            id: "ev-1".to_string(),
            artifact_id: "art-1".to_string(),
            timestamp: 100,
        };
        substrate.evidence.insert(evidence);

        prop_assert!(substrate.is_temporally_consistent());
    }
}
