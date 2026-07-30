//! Kani verification for ARKHE v7.0 — Projection Engine

use std::collections::HashSet;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ProjectionState {
    pub substrate: Substrate,
    pub view: View,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Substrate {
    pub data: HashSet<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct View {
    pub projected: HashSet<String>,
}

impl Substrate {
    pub fn project(&self) -> View {
        View {
            projected: self.data.clone(),
        }
    }
}

#[cfg(kani)]
mod verification {
    use super::*;

    #[kani::proof]
    pub fn projection_purity() {
        let s = kani::any::<Substrate>();
        let before = s.clone();
        let _v = s.project();
        assert_eq!(before, s);
    }

    #[kani::proof]
    pub fn projection_determinism() {
        let s1 = kani::any::<Substrate>();
        let s2 = s1.clone();
        let v1 = s1.project();
        let v2 = s2.project();
        assert_eq!(v1, v2);
    }
}