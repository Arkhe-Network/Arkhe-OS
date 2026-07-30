//! Kani verification for ARKHE v7.0 — IC1 and IC3

use std::collections::{HashMap, HashSet};

// ─── Types ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Artifact {
    pub id: String,
    pub data: String,
}

#[derive(Debug, Clone)]
pub struct Substrate {
    pub artifacts: HashMap<String, Artifact>,
    pub evidence: HashSet<Evidence>,
    pub assertions: HashSet<Assertion>,
    pub claims: HashSet<Claim>,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Evidence {
    pub id: String,
    pub artifact_id: String,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Assertion {
    pub id: String,
    pub evidence_ids: Vec<String>,
    pub claim: Option<Claim>,
    pub references: Vec<String>, // IDs de Artifacts
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Claim {
    pub id: String,
    pub confidence: u64,
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

    /// Retorna a identidade canônica de um artifact
    pub fn canonical_id(&self, artifact: &Artifact) -> Option<String> {
        self.artifacts
            .iter()
            .find(|(_, a)| a == artifact)
            .map(|(id, _)| id.clone())
    }

    /// Retorna as evidências associadas a uma assertion
    pub fn evidence_of(&self, assertion: &Assertion) -> Vec<Evidence> {
        assertion
            .evidence_ids
            .iter()
            .filter_map(|id| self.evidence.iter().find(|e| e.id == *id))
            .cloned()
            .collect()
    }

    /// Projeta o substrate em uma visão (pura, não modifica)
    pub fn project(&self) -> View {
        View {
            artifacts: self.artifacts.clone(),
            evidence: self.evidence.clone(),
            assertions: self.assertions.clone(),
            claims: self.claims.clone(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct View {
    pub artifacts: HashMap<String, Artifact>,
    pub evidence: HashSet<Evidence>,
    pub assertions: HashSet<Assertion>,
    pub claims: HashSet<Claim>,
}

// ─── Kani Verification ───────────────────────────────────────────────────

#[cfg(kani)]
mod verification {
    use super::*;

    // ─── IC1: Canonical Identity ────────────────────────────────────────

    #[kani::proof]
    pub fn ic1_canonical_identity() {
        // Dado dois artifacts quaisquer
        let a = kani::any::<Artifact>();
        let b = kani::any::<Artifact>();

        // Assumir que eles têm a mesma identidade canônica
        let substrate = Substrate::new();
        // Inserir artifacts no substrato
        let mut substrate = substrate;
        let id_a = format!("{}", kani::any::<u32>());
        let id_b = format!("{}", kani::any::<u32>());

        substrate.artifacts.insert(id_a.clone(), a.clone());
        substrate.artifacts.insert(id_b.clone(), b.clone());

        // Se as identidades são iguais
        if let Some(canon_a) = substrate.canonical_id(&a) {
            if let Some(canon_b) = substrate.canonical_id(&b) {
                if canon_a == canon_b {
                    // Então os artifacts são iguais (propriedade IC1)
                    assert_eq!(a, b);
                }
            }
        }
    }

    // ─── IC3: Projection Purity ────────────────────────────────────────

    #[kani::proof]
    pub fn ic3_projection_purity() {
        // Dado um substrate qualquer
        let substrate = kani::any::<Substrate>();
        let mut substrate = substrate;

        // Projetar (não deve modificar o substrate)
        let before = substrate.clone();
        let _view = substrate.project();

        // O substrato deve permanecer inalterado
        assert_eq!(before, substrate);
    }

    // ─── IC4: Determinism ──────────────────────────────────────────────

    #[kani::proof]
    pub fn ic4_determinism() {
        // Dados dois substrates iguais
        let s1 = kani::any::<Substrate>();
        let s2 = s1.clone();

        // As projeções devem ser iguais
        let v1 = s1.project();
        let v2 = s2.project();

        assert_eq!(v1, v2);
    }

    // ─── IC6: Referential Integrity ────────────────────────────────────

    #[kani::proof]
    pub fn ic6_referential_integrity() {
        // Dado um substrate e uma assertion
        let substrate = kani::any::<Substrate>();
        let assertion = kani::any::<Assertion>();

        // Verificar que toda referência existe no substrate
        for ref_id in &assertion.references {
            assert!(substrate.artifacts.contains_key(ref_id));
        }
    }
}

// ─── Proptest (para execução em CI) ──────────────────────────────────

#[cfg(test)]
mod proptest {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        /// IC1 — a identidade canônica é única
        #[test]
        fn ic1_canonical_identity_unique(a: Artifact, b: Artifact) {
            let mut substrate = Substrate::new();
            let id_a = format!("{}", rand::random::<u32>());
            let id_b = format!("{}", rand::random::<u32>());

            substrate.artifacts.insert(id_a.clone(), a.clone());
            substrate.artifacts.insert(id_b.clone(), b.clone());

            if let Some(canon_a) = substrate.canonical_id(&a) {
                if let Some(canon_b) = substrate.canonical_id(&b) {
                    if canon_a == canon_b {
                        prop_assert_eq!(a, b);
                    }
                }
            }
        }

        /// IC3 — a projeção não modifica o substrato
        #[test]
        fn ic3_projection_does_not_modify_substrate(mut substrate: Substrate) {
            let before = substrate.clone();
            let _view = substrate.project();
            prop_assert_eq!(before, substrate);
        }
    }
}