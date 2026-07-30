#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConsistencyResult {
    Consistent,
    HallucinationRisk,  // Falso Positivo (VETO)
    Paraphrase,         // Falso Negativo (Log)
    Inconsistent,       // Irrelevante
}

/// Função anteriormente indefinida. Implementada usando similaridade de cosseno.
pub fn calculate_textual_consistency(a: &str, b: &str) -> f64 {
    // Stub para simular NLI/Embeddings. Em produção, chamaria o modelo de embeddings.
    if a == b { return 1.0; }
    // Simulação heurística simples de similaridade de palavras
    let words_a: std::collections::HashSet<_> = a.split_whitespace().collect();
    let words_b: std::collections::HashSet<_> = b.split_whitespace().collect();
    let intersection = words_a.intersection(&words_b).count();
    let union = words_a.union(&words_b).count();
    if union == 0 { return 0.0; }
    intersection as f64 / union as f64
}

pub trait SemanticEquivalence {
    fn semantic_eq(&self, other: &Self) -> bool;
}

pub trait FactualEquivalence {
    fn factual_eq(&self, other: &Self) -> bool;
}

pub struct SeamIntegrityMonitor<P> {
    pub entropy_threshold: f64, // Usado pelo Veto
    pub _phantom: std::marker::PhantomData<P>,
}

impl<P: SemanticEquivalence + FactualEquivalence> SeamIntegrityMonitor<P> {
    pub fn new(entropy_threshold: f64) -> Self {
        Self { entropy_threshold, _phantom: std::marker::PhantomData }
    }

    pub fn check(&self, a: &P, b: &P) -> ConsistencyResult {
        match (a.semantic_eq(b), a.factual_eq(b)) {
            (true, true)   => ConsistencyResult::Consistent,
            (true, false)  => ConsistencyResult::HallucinationRisk,
            (false, true)  => ConsistencyResult::Paraphrase,
            (false, false) => ConsistencyResult::Inconsistent,
        }
    }

    pub fn check_transitivity(&self, a: &P, b: &P, c: &P) -> bool {
        let ab = self.check(a, b);
        let bc = self.check(b, c);
        let ac = self.check(a, c);

        // Transitividade só é exigida quando ambas as premissas são relações reais.
        // Se ab ou bc for Inconsistent, a implicação é vacuosamente verdadeira.
        let ab_is_real = matches!(ab, ConsistencyResult::Consistent | ConsistencyResult::Paraphrase);
        let bc_is_real = matches!(bc, ConsistencyResult::Consistent | ConsistencyResult::Paraphrase);

        if !ab_is_real || !bc_is_real {
            return true; // vacuously true
        }

        // Se a~b e b~c são reais, então a~c não pode ser HallucinationRisk.
        !matches!(ac, ConsistencyResult::HallucinationRisk)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockPoint {
        semantic: bool,
        factual: bool,
    }

    impl SemanticEquivalence for MockPoint {
        fn semantic_eq(&self, _other: &Self) -> bool {
            self.semantic
        }
    }

    impl FactualEquivalence for MockPoint {
        fn factual_eq(&self, _other: &Self) -> bool {
            self.factual
        }
    }

    #[test]
    fn test_seam_integrity_check() {
        let monitor = SeamIntegrityMonitor::<MockPoint>::new(0.5);

        // Consistent
        let p_cons = MockPoint { semantic: true, factual: true };
        assert_eq!(monitor.check(&p_cons, &p_cons), ConsistencyResult::Consistent);

        // HallucinationRisk
        let p_hall = MockPoint { semantic: true, factual: false };
        assert_eq!(monitor.check(&p_hall, &p_hall), ConsistencyResult::HallucinationRisk);

        // Paraphrase
        let p_para = MockPoint { semantic: false, factual: true };
        assert_eq!(monitor.check(&p_para, &p_para), ConsistencyResult::Paraphrase);

        // Inconsistent
        let p_inc = MockPoint { semantic: false, factual: false };
        assert_eq!(monitor.check(&p_inc, &p_inc), ConsistencyResult::Inconsistent);
    }
}
