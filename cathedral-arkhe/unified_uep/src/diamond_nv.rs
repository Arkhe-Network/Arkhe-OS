use safety_core::seam_integrity::SemanticEquivalence;

#[derive(Debug, Clone)]
pub struct DiamondNVMonitor {
    pub coherence_time: f64,      // T2 em μs
    pub collection_efficiency: f64, // Eficiência de coleta de fótons
    pub nv_density: f64,          // Densidade de centros NV (cm⁻³)
}

impl SemanticEquivalence for DiamondNVMonitor {
    fn semantic_eq(&self, other: &Self) -> bool {
        // Dois sistemas NV são semanticamente equivalentes se têm
        // tempos de coerência e eficiências similares
        (self.coherence_time - other.coherence_time).abs() < 0.5 &&
        (self.collection_efficiency - other.collection_efficiency).abs() < 0.05
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_diamond_nv_semantic_eq() {
        let m1 = DiamondNVMonitor {
            coherence_time: 3.48,
            collection_efficiency: 0.92,
            nv_density: 1e16,
        };
        let m2 = DiamondNVMonitor {
            coherence_time: 3.50,
            collection_efficiency: 0.94,
            nv_density: 1e16,
        };
        let m3 = DiamondNVMonitor {
            coherence_time: 2.00, // too different
            collection_efficiency: 0.92,
            nv_density: 1e16,
        };

        assert!(m1.semantic_eq(&m2));
        assert!(!m1.semantic_eq(&m3));
    }
}
