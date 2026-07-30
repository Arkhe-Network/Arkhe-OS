// ═══════════════════════════════════════════════════════════════════════════════
// recursive_improvement.rs — Substrato 1300.2: Real Distillation + CreekGuard
// Selo: CATHEDR-1300.2-DISTILLATION-v1.0.0-2026-06-13
// Arquiteto: ORCID 0009-0005-2697-4668
// ═══════════════════════════════════════════════════════════════════════

use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};
use serde::{Serialize, Deserialize};
use sha3::{Sha3_256, Digest};

// =============================================================================
// Distillation Types
// =============================================================================

/// Strategy for selecting distillation data from outputs
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum DistillationStrategy {
    /// Use all outputs as training data (maximum data, possible PII leakage)
    AllOutputs,
    /// Use only outputs with quality_score >= threshold
    QualityFiltered { min_score: f64 },
    /// Use top-k by diversity (maximize coverage of capability space)
    TopK { k: usize },
    /// Use outputs from specific domains only
    DomainFiltered { domains: Vec<String> },
    /// Use outputs where entropy is within [min, max] range (curriculum learning)
    EntropyBounded { min: f64, max: f64 },
    /// Use only outputs with low CreekGuard anomaly score
    CreekGuardFiltered { max_anomaly: f64 },
}

impl Default for DistillationStrategy {
    fn default() -> Self {
        Self::QualityFiltered { min_score: 0.7 }
    }
}

/// A distilled training example ready for fine-tuning.
/// IMPORTANT: All PII and sensitive data must be stripped before distillation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DistilledExample {
    /// Unique ID (SHA-256 hash of content + metadata)
    pub id: String,

    /// The input prompt (sanitized of PII)
    pub prompt: String,

    /// The model output (sanitized of PII)
    pub output: String,

    /// Quality score of the output (from benchmark evaluation)
    pub quality_score: f64,

    /// Entropy of the output
    pub output_entropy: f64,

    /// Domain classification
    pub domain: String,

    /// Entropy of the input prompt
    pub prompt_entropy: f64,

    /// Switch count from SwiReasoning (if available)
    pub switch_count: usize,

    /// CreekGuard anomaly score (0.0 = clean, 1.0 = suspicious)
    pub creekguard_anomaly: f64,

    /// Metadata for filtering
    pub tags: Vec<String>,

    /// Hash of the original (pre-sanitization) content for deduplication
    pub original_content_hash: String,

    /// Whether this example passed all filters
    pub is_clean: bool,

    /// Whether PII was found and removed
    pub pii_removed: bool,

    /// Version of distillation pipeline
    pub distillation_version: String,

    pub pii_removed_types: Vec<PIIType>,
    pub pii_removed_spans: Vec<PIISpan>,
}

/// PII detection result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIIFinding {
    pub found_pii: bool,
    pub pii_types: Vec<PIIType>,
    pub sanitized_content: String,
    pub removed_spans: Vec<PIISpan>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PIIType {
    Email,
    Phone,
    SSN,
    CreditCard,
    Address,
    Name,
    DateOfBirth,
    IdNumber,
    IpAddress,
    PassportNumber,
    FinancialAccount,
    MedicalRecord,
    LegalDocument,
    PersonalName,
    Organization,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PIISpan {
    pub start: usize,
    pub end: usize,
    pub pii_type: PIIType,
    pub context: String,
}

// =============================================================================
// PII Detector
// =============================================================================

/// Detects and sanitizes PII from text
pub struct PIIDetector {
    /// Regex patterns for PII detection
    patterns: Vec<(PIIType, regex::Regex)>,
    /// Additional string patterns (simple substring matching for speed)
    simple_patterns: Vec<(PIIType, String)>,
}

impl PIIDetector {
    pub fn new() -> Self {
        let patterns = vec![
            // Regex-based patterns (compiled once)
            (PIIType::Email, regex::Regex::new(r"(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
                .expect("email regex should be valid")),
            (PIIType::Phone, regex::Regex::new(r"(?:\+?\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4})")
                .expect("phone regex should be valid")),
            (PIIType::SSN, regex::Regex::new(r"\b\d{3}[- ]?\d{2}[-.\s]?\d{4}\b")
                .expect("SSN regex should be valid")),
            (PIIType::CreditCard, regex::Regex::new(r"(?:\d{4}[- ]?\d{4}[-.\s]?\d{4}\b)")
                .expect("credit card regex should be valid")),
            (PIIType::Address, regex::Regex::new(r"\d+ [A-Za-z]+(?:\s+[A-Za-z]+\d*|St\.?)")
                .expect("address regex should be valid")),
            (PIIType::DateOfBirth, regex::Regex::new(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
                .expect("DOB regex should be valid")),
            (PIIType::IdNumber, regex::Regex::new(r"\d{6,9}")
                .expect("ID number regex should be valid")),
            (PIIType::IpAddress, regex::Regex::new(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
                .expect("IP regex should be valid")),
        ];

        // Simple string patterns (faster for large batches, lower recall)
        let simple_patterns = vec![
            (PIIType::PassportNumber, "passport".to_string()),
            (PIIType::Name, "nome:".to_string()),
            (PIIType::Organization, "inc.".to_string()),
            (PIIType::FinancialAccount, "conta".to_string()),
            (PIIType::LegalDocument, "lei".to_string()),
            (PIIType::PersonalName, " da Silva".to_string()),
        ];

        Self { patterns, simple_patterns }
    }

    /// Detect PII in text
    pub fn detect_pii(&self, text: &str) -> PIIFinding {
        let mut found_pii = false;
        let mut all_types = HashSet::new();
        let mut all_spans: Vec<PIISpan> = Vec::new();
        let mut sanitized = text.to_string();

        // Regex-based detection
        for (pii_type, regex) in &self.patterns {
            let mut replacements = Vec::new();
            for mat in regex.find_iter(&sanitized) {
                found_pii = true;
                all_types.insert(*pii_type);
                let span = mat.range();
                all_spans.push(PIISpan {
                    start: span.start,
                    end: span.end,
                    pii_type: *pii_type,
                    context: sanitized[span.start..span.end].to_string(),
                });
                replacements.push((span, format!("[REDACTED-{:?}]", pii_type)));
            }
            for (span, replacement) in replacements.into_iter().rev() {
                sanitized.replace_range(span, &replacement);
            }
        }

        // Simple string-based detection (complement regex for speed)
        for (pii_type, pattern) in &self.simple_patterns {
            let mut start = 0;
            while let Some(pos) = sanitized[start..].find(pattern) {
                found_pii = true;
                all_types.insert(*pii_type);
                let actual_pos = start + pos;
                let end = (actual_pos + pattern.len()).min(sanitized.len());
                all_spans.push(PIISpan {
                    start: actual_pos,
                    end,
                    pii_type: *pii_type,
                    context: sanitized[actual_pos..end].to_string(),
                });

                let replacement = format!("[REDACTED-{:?}]", pii_type);
                sanitized.replace_range(actual_pos..end, &replacement);
                start = actual_pos + replacement.len(); // Continue searching (may have multiple occurrences)
            }
        }

        PIIFinding {
            found_pii,
            pii_types: all_types.into_iter().collect(),
            sanitized_content: sanitized,
            removed_spans: all_spans,
        }
    }
}

// =============================================================================
// Distillation Pipeline
// =============================================================================

/// Configuration for the distillation pipeline
#[derive(Debug, Clone, Serialize,Deserialize)]
pub struct DistillationConfig {
    /// Strategy for selecting training data
    pub strategy: DistillationStrategy,

    /// Minimum quality score for quality-filtered strategy
    pub min_quality_score: f64,

    /// k for top-k strategy
    pub top_k: usize,

    /// Domain filter
    pub domain_filter: Option<Vec<String>>,

    /// Entropy bounds for entropy-bounded strategy
    pub entropy_min: Option<f64>,
    pub entropy_max: Option<f64>,

    /// CreekGuard max anomaly threshold (0.0 = block all, 1.0 = allow all)
    pub creek_max_anomaly: f64,

    /// Whether to apply PII sanitization
    pub sanitize_pii: bool,

    /// Maximum examples to generate (0 = unlimited)
    pub max_examples: Option<usize>,

    /// Output file for distilled data
    pub output_path: String,

    /// Include switch count in output
    pub include_switch_count: bool,

    /// Version tag for lineage tracking
    pub version: String,
}

impl Default for DistillationConfig {
    fn default() -> Self {
        Self {
            strategy: DistillationStrategy::QualityFiltered { min_score: 0.7 },
            min_quality_score: 0.7,
            top_k: 1000,
            domain_filter: None,
            entropy_min: Some(0.3),
            entropy_max: Some(0.8),
            creek_max_anomaly: 0.3,
            sanitize_pii: true,
            max_examples: None,
            output_path: "distilled_data.jsonl".to_string(),
            include_switch_count: true,
            version: "1.0.0".to_string(),
        }
    }
}

/// Result of a distillation run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DistillationResult {
    pub config: DistillationConfig,
    pub total_inputs: usize,
    pub filtered_inputs: usize,
    pub pii_removed: usize,
    pub creek_blocked: usize,
    pub final_examples: Vec<DistilledExample>,
    pub output_path: String,
    pub wall_time_ms: u64,
    pub version: String,
}

impl DistillationResult {
    pub fn is_clean(&self) -> bool {
        self.final_examples.iter().all(|e| e.is_clean)
    }
}

/// The distillation pipeline itself
pub struct DistillationPipeline {
    config: DistillationConfig,
    pii_detector: PIIDetector,
    creek_guard: Arc<arkhe_security::CreekGuard>,
}

impl DistillationPipeline {
    pub fn new(config: DistillationConfig) -> Self {
        Self {
            config,
            pii_detector: PIIDetector::new(),
            creek_guard: Arc::new(arkhe_security::CreekGuard),
        }
    }

    /// Run the full distillation pipeline
    pub fn distill(
        &self,
        inputs: &[&DistilledExample],
    ) -> Result<DistillationResult, String> {
        let total = inputs.len();
        let mut filtered: Vec<DistilledExample> = Vec::new();
        let mut pii_removed = 0;
        let mut creek_blocked = 0;

        for input in inputs {
            // Step 1: PII Detection & Sanitization
            let finding = self.pii_detector.detect_pii(&input.output);
            let mut example = (*input).clone();

            if finding.found_pii {
                pii_removed += 1;
                example.pii_removed_types = finding.pii_types.clone();
                example.pii_removed_spans = finding.removed_spans;
                example.is_clean = false;
                example.pii_removed = true;

                // Sanitize
                example.output = finding.sanitized_content;
            } else {
                example.is_clean = true;
            }

            // Step 2: CreekGuard covert channel detection
            if self.creek_guard.check_output(&example.output) > self.config.creek_max_anomaly {
                creek_blocked += 1;
                example.is_clean = false;
            }

            // Step 3: Strategy-based filtering
            let passes_filter = match &self.config.strategy {
                DistillationStrategy::AllOutputs => true,

                DistillationStrategy::QualityFiltered { min_score } => {
                    example.quality_score >= *min_score
                }

                DistillationStrategy::TopK { k: _ } => {
                    true // Placeholder
                }

                DistillationStrategy::DomainFiltered { domains } => {
                    domains.contains(&example.domain)
                }

                DistillationStrategy::EntropyBounded { min, max } => {
                    (example.output_entropy >= *min)
                        & (example.output_entropy <= *max)
                }

                DistillationStrategy::CreekGuardFiltered { max_anomaly } => {
                    example.creekguard_anomaly <= *max_anomaly
                }
            };

            if passes_filter {
                example.distillation_version = self.config.version.clone();
                filtered.push(example);
            }
        }

        // Step 4: Deduplication by original content hash
        let mut deduped: Vec<DistilledExample> = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();

        for example in filtered.iter() {
            if seen.insert(example.original_content_hash.clone()) {
                deduped.push(example.clone());
            }
        }

        // Step 5: Apply max_examples limit
        let final_examples: Vec<DistilledExample> = match self.config.max_examples {
            Some(max) => deduped.into_iter().take(max).collect(),
            None => deduped,
        };

        let wall_time_ms = 0; // mocked

        let result = DistillationResult {
            config: self.config.clone(),
            total_inputs: total,
            filtered_inputs: filtered.len(),
            pii_removed,
            creek_blocked,
            final_examples: final_examples,
            output_path: self.config.output_path.clone(),
            wall_time_ms,
            version: self.config.version.clone(),
        };

        Ok(result)
    }
}

pub mod arkhe_security {
    pub struct CreekGuard;
    impl CreekGuard {
        pub fn check_output(&self, _text: &str) -> f64 {
            0.0 // Mocked
        }
    }
}
