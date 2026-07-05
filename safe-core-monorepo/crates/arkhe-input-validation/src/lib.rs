//! Validação de entrada para sistemas de IA.
//! Alinhado com AISVS C2.1.1–C2.1.5, C2.1.7, C2.1.8.
//!
//! ✅ F8: Normalização agora é aplicada, não apenas detectada.

use arkhe_core::ArkheResult;
use regex::Regex;
use std::collections::HashSet;
use unicode_normalization::UnicodeNormalization;

mod charset;
mod length;
mod encoding;
mod many_shot;

pub use charset::CharacterSetValidator;
pub use length::LengthValidator;
pub use encoding::EncodingValidator;
pub use many_shot::ManyShotDetector;

/// Resultado da validação de entrada.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationResult {
    pub valid: bool,
    pub reason: Option<String>,
    /// ✅ F8: Sempre populada com a versão normalizada.
    pub normalized: String,
}

/// Validador combinado para todas as verificações.
pub struct InputValidator {
    length: LengthValidator,
    charset: CharacterSetValidator,
    encoding: EncodingValidator,
    many_shot: ManyShotDetector,
    max_tokens: usize,
}

impl InputValidator {
    pub fn new(max_tokens: usize) -> Self {
        Self {
            length: LengthValidator::new(max_tokens),
            charset: CharacterSetValidator::new(),
            encoding: EncodingValidator::new(),
            many_shot: ManyShotDetector::new(),
            max_tokens,
        }
    }

    /// ✅ F8: Valida e retorna a string NORMALIZADA (não a original).
    /// Se inválida, retorna erro com razão mas ainda retorna a versão normalizada
    /// para logging/análise.
    pub fn validate(&self, input: &str) -> ArkheResult<ValidationResult> {
        // C2.1.1: Normalização — SEMPRE aplicada primeiro
        let normalized: String = input.nfc().collect();

        // C2.1.4: Controle de comprimento (rejeitar, não truncar)
        if !self.length.validate(&normalized) {
            return Ok(ValidationResult {
                valid: false,
                reason: Some(format!(
                    "Input exceeds maximum length ({} tokens estimated, max {})",
                    self.length.estimate_tokens(&normalized),
                    self.max_tokens
                )),
                normalized, // ✅ Retorna normalizada mesmo se inválido
            });
        }

        // C2.1.5: Restrição de conjunto de caracteres (allow-list)
        if !self.charset.validate(&normalized) {
            return Ok(ValidationResult {
                valid: false,
                reason: Some("Input contains disallowed characters".into()),
                normalized,
            });
        }

        // C2.1.7: Tokens especiais reservados
        if self.encoding.has_reserved_tokens(&normalized) {
            return Ok(ValidationResult {
                valid: false,
                reason: Some("Input contains reserved special tokens".into()),
                normalized,
            });
        }

        // C2.1.8: Detecção de many-shot jailbreak
        if self.many_shot.detect(&normalized) {
            return Ok(ValidationResult {
                valid: false,
                reason: Some("Potential many-shot jailbreak detected".into()),
                normalized,
            });
        }

        Ok(ValidationResult {
            valid: true,
            reason: None,
            normalized,
        })
    }

    /// Versão simplificada que retorna bool.
    pub fn is_valid(&self, input: &str) -> bool {
        self.validate(input).map(|r| r.valid).unwrap_or(false)
    }
}

impl Default for InputValidator {
    fn default() -> Self {
        Self::new(4096)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalization_applied() {
        let v = InputValidator::new(1000);
        // "é" pode ser NFC ou NFD. NFC: 1 codepoint, NFD: e + combining acute
        let nfd_input = "e\u{0301}"; // NFD: e + combining acute accent
        let result = v.validate(nfd_input).unwrap();
        assert!(result.valid);
        // Verificar que foi normalizado para NFC
        assert_eq!(result.normalized, "é");
        assert_ne!(result.normalized, nfd_input);
    }

    #[test]
    fn test_invalid_still_returns_normalized() {
        let v = InputValidator::new(5);
        let long_input = "a".repeat(100);
        let result = v.validate(&long_input).unwrap();
        assert!(!result.valid);
        assert!(!result.normalized.is_empty()); // ✅ Ainda retorna normalizada
    }
}
