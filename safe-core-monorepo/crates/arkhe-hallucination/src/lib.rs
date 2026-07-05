//! ⚠️ STUB ARQUITETURAL — Não é detecção real de alucinações.
//!
//! Este módulo define a estrutura para detecção de alucinações mas a lógica
//! atual (overlap de palavras + temperatura scaling) é insuficiente para
//! produção. Requer:
//! - Embeddings reais para similaridade semântica
//! - Calibração com dados anotados
//! - Opcionalmente: Monte Carlo Dropout
//!
//! Score de maturidade: 30/100 — estrutura correta, lógica insuficiente.

#![warn(missing_docs)]

use serde::{Deserialize, Serialize};

/// Método usado para estimativa de confiança.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ConfidenceMethod {
    /// Calibração por temperatura (simplificada).
    TemperatureScaling,
    /// Consistência semântica via overlap de palavras (fraco).
    SemanticOverlap,
    /// Combinado: 70% calibrated + 30% semantic.
    Combined,
    /// Monte Carlo Dropout (não implementado).
    MCDropout,
}

/// Estimativa de confiança da resposta.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceEstimate {
    /// Score de confiança (0.0–1.0).
    pub score: f32,
    /// Se o score está calibrado com dados reais.
    pub calibrated: bool,
    /// Método usado.
    pub method: ConfidenceMethod,
}

/// Resultado da detecção de alucinação.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HallucinationResult {
    /// Se alucinação foi detectada.
    pub is_hallucination: bool,
    /// Confiança na resposta.
    pub confidence: ConfidenceEstimate,
    /// Explicação.
    pub explanation: String,
}

/// Detector de alucinações (stub).
pub struct HallucinationDetector {
    /// Threshold abaixo do qual consideramos possível alucinação.
    threshold: f32,
}

impl Default for HallucinationDetector {
    fn default() -> Self {
        Self { threshold: 0.65 }
    }
}

impl HallucinationDetector {
    pub fn new(threshold: f32) -> Self {
        Self { threshold }
    }

    /// Detecta alucinação comparando resposta com contexto.
    ///
    /// ⚠️ STUB: Usa overlap de palavras — métrica muito fraca.
    /// Em produção, substituir por cosine similarity de embeddings.
    pub fn detect(
        &self,
        response: &str,
        context: &str,
        _temperature: f32,
    ) -> HallucinationResult {
        let response_words: std::collections::HashSet<&str> =
            response.split_whitespace().collect();
        let context_words: std::collections::HashSet<&str> =
            context.split_whitespace().collect();

        // Overlap: quantas palavras da resposta aparecem no contexto
        let overlap: f32 = response_words
            .intersection(&context_words)
            .count() as f32
            / response_words.len().max(1) as f32;

        let semantic_confidence = overlap.clamp(0.0, 1.0);

        // Temperature scaling simplificado
        let temp_confidence = 0.7; // stub — não usa temperatura real

        // Combined: 70% calibrated + 30% semantic
        let combined = 0.7 * temp_confidence + 0.3 * semantic_confidence;

        HallucinationResult {
            is_hallucination: combined < self.threshold,
            confidence: ConfidenceEstimate {
                score: combined,
                calibrated: false,
                method: ConfidenceMethod::Combined,
            },
            explanation: if combined < self.threshold {
                format!(
                    "Low confidence ({:.2}) — response has low overlap ({:.2}) with context",
                    combined, overlap
                )
            } else {
                format!("Confidence OK ({:.2})", combined)
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_high_overlap_not_hallucination() {
        let detector = HallucinationDetector::new(0.5);
        let result = detector.detect(
            "BLAKE3 is a hash function designed for speed",
            "BLAKE3 is a cryptographic hash function that is faster than SHA-256 and BLAKE2",
            0.7,
        );
        assert!(!result.is_hallucination);
    }

    #[test]
    fn test_no_overlap_is_hallucination() {
        let detector = HallucinationDetector::new(0.5);
        let result = detector.detect(
            "The answer is 42 because quantum mechanics proves it",
            "BLAKE3 is a hash function",
            0.7,
        );
        assert!(result.is_hallucination);
    }
}
