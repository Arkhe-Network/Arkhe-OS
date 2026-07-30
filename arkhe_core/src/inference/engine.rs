// File: arkhe_core/src/inference/engine.rs
// Substrato 1104.2 — Rio-3.5-Open-397B Integration v1.1.0 (COMPLETE)
// Selo: CATHEDRAL-1104.2-ENGINE-COMPLETE-v1.1.0-2026-06-13
// Arquiteto: ORCID 0009-0005-2697-4668

use arkhe_cognitive::swireasoning::{SwiReasoningConfig, ReasoningMode};
use arkhe_security::tee::{TEEContext, EnclaveType, AttestationMode};
use arkhe_chain::pqc::sphincs::{SphincsPlusKey, SphincsPlusSignature};

// ============================================================
// DOMAIN DEFINITIONS
// ============================================================

/// Task domain classification for capability routing.
/// Mirrors the calibration domains used in run_chat.py calibration samples.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Domain {
    /// General-purpose queries (fallback)
    General,

    /// Portuguese legal domain (contracts, legislation, jurisprudence)
    PortugueseLegal,

    /// Portuguese technical domain (engineering, IT, science)
    PortugueseTechnical,

    /// Agentic software engineering (coding, debugging, architecture)
    AgenticCoding,

    /// Multimodal vision-language tasks
    MultimodalVision,

    /// Pure mathematics and formal proofs
    Mathematics,

    /// STEM (science, technology, engineering, mathematics)
    STEM,

    /// Ultra-complex reasoning (Apex-level benchmarks)
    ReasoningUltra,

    /// Temporal/retrocausal analysis (PCT domain)
    TemporalAnalysis,

    /// Post-quantum cryptography and security
    PostQuantumSecurity,

    /// Blockchain governance and smart contracts
    BlockchainGovernance,

    /// Chinese technical domain
    ChineseTechnical,

    /// English scientific literature
    EnglishScientific,
}

impl Domain {
    /// Returns the canonical string identifier for logging and metrics.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::General => "general",
            Self::PortugueseLegal => "portuguese_legal",
            Self::PortugueseTechnical => "portuguese_technical",
            Self::AgenticCoding => "agentic_coding",
            Self::MultimodalVision => "multimodal_vision",
            Self::Mathematics => "mathematics",
            Self::STEM => "stem",
            Self::ReasoningUltra => "reasoning_ultra",
            Self::TemporalAnalysis => "temporal_analysis",
            Self::PostQuantumSecurity => "post_quantum_security",
            Self::BlockchainGovernance => "blockchain_governance",
            Self::ChineseTechnical => "chinese_technical",
            Self::EnglishScientific => "english_scientific",
        }
    }

    /// Returns the preferred language bias for SwiReasoning calibration.
    pub fn language_bias(&self) -> LanguageBias {
        match self {
            Self::PortugueseLegal | Self::PortugueseTechnical => LanguageBias::PortugueseTechnical,
            Self::ChineseTechnical => LanguageBias::ChineseTechnical,
            Self::EnglishScientific | Self::STEM | Self::Mathematics => LanguageBias::EnglishScientific,
            _ => LanguageBias::General,
        }
    }
}

// ============================================================
// TASK DEFINITION
// ============================================================

/// A task to be executed by an inference engine.
/// Contains the prompt, domain classification, and execution constraints.
#[derive(Debug, Clone)]
pub struct Task {
    /// Unique task identifier (SHA-256 truncated)
    pub id: String,

    /// The prompt text (UTF-8)
    pub prompt: String,

    /// Domain classification for capability-based routing
    pub domain: Domain,

    /// Maximum output tokens allowed
    pub max_tokens: usize,

    /// Temperature for sampling (0.0 = deterministic, 1.0 = creative)
    pub temperature: f64,

    /// Top-p nucleus sampling threshold
    pub top_p: f64,

    /// Whether multimodal input (images) is present
    pub has_image: bool,

    /// Whether the task requires TEE isolation
    pub requires_tee: bool,

    /// Whether the task requires PQC anchoring to RBB Chain
    pub requires_pqc_anchor: bool,

    /// Priority level (0 = highest, 255 = lowest)
    pub priority: u8,

    /// Maximum latency budget in microseconds
    pub latency_budget_us: u64,

    /// SwiReasoning override (None = use engine default)
    pub swi_override: Option<SwiReasoningConfig>,
}

impl Task {
    /// Create a new task with sensible defaults.
    pub fn new(prompt: impl Into<String>, domain: Domain) -> Self {
        let prompt_str = prompt.into();
        let id = format!("{:x}", {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut hasher = DefaultHasher::new();
            prompt_str.hash(&mut hasher);
            hasher.finish()
        })[..16].to_string();

        Self {
            id,
            prompt: prompt_str,
            domain,
            max_tokens: 2048,
            temperature: 0.6,
            top_p: 0.95,
            has_image: false,
            requires_tee: true,
            requires_pqc_anchor: true,
            priority: 128,
            latency_budget_us: 30_000_000, // 30s default
            swi_override: None,
        }
    }

    /// Set maximum tokens and return self (builder pattern).
    pub fn with_max_tokens(mut self, max_tokens: usize) -> Self {
        self.max_tokens = max_tokens;
        self
    }

    /// Set temperature and return self.
    pub fn with_temperature(mut self, temp: f64) -> Self {
        self.temperature = temp.clamp(0.0, 2.0);
        self
    }

    /// Set TEE requirement.
    pub fn with_tee(mut self, required: bool) -> Self {
        self.requires_tee = required;
        self
    }

    /// Set PQC anchor requirement.
    pub fn with_pqc_anchor(mut self, required: bool) -> Self {
        self.requires_pqc_anchor = required;
        self
    }

    /// Set latency budget.
    pub fn with_latency_budget(mut self, us: u64) -> Self {
        self.latency_budget_us = us;
        self
    }

    /// Override SwiReasoning config.
    pub fn with_swi_config(mut self, config: SwiReasoningConfig) -> Self {
        self.swi_override = Some(config);
        self
    }

    /// Compute the prompt hash for integrity verification.
    pub fn prompt_hash(&self) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.prompt.hash(&mut hasher);
        format!("{:x}", hasher.finish())[..16].to_string()
    }
}

// ============================================================
// LANGUAGE BIAS
// ============================================================

/// Language bias for SwiReasoning calibration.
/// Affects entropy_ref_x1000 defaults and tokenization behavior.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LanguageBias {
    General,
    PortugueseTechnical,
    PortugueseLegal,
    ChineseTechnical,
    EnglishScientific,
}

impl LanguageBias {
    /// Default entropy_ref_x1000 for this language bias.
    pub fn default_entropy_ref_x1000(&self) -> u32 {
        match self {
            Self::General => 380,
            Self::PortugueseTechnical => 420,
            Self::PortugueseLegal => 440,
            Self::ChineseTechnical => 360,
            Self::EnglishScientific => 400,
        }
    }

    /// Default max_switches for this language bias.
    pub fn default_max_switches(&self) -> u32 {
        match self {
            Self::General => 6,
            Self::PortugueseTechnical => 8,
            Self::PortugueseLegal => 10,
            Self::ChineseTechnical => 6,
            Self::EnglishScientific => 8,
        }
    }
}

// ============================================================
// SWIREASONING CONFIG
// ============================================================

/// SwiReasoning configuration for dynamic explicit/latent switching.
/// Calibrated per domain and language bias.
#[derive(Debug, Clone)]
pub struct SwiReasoningConfig {
    /// Entropy reference threshold (×1000 for integer precision).
    /// e.g., 420 = 0.42 nats.
    pub entropy_ref_x1000: u32,

    /// Maximum number of mode switches allowed per inference.
    pub max_switches: u32,

    /// Block size for block-wise confidence estimation.
    pub block_size: usize,

    /// Hidden-space exploration depth in latent mode.
    pub latent_depth: usize,

    /// Confidence threshold (×1000) to commit from latent to explicit.
    pub explicit_commit_threshold: u32,

    /// Language bias affecting entropy calibration.
    pub language_bias: LanguageBias,

    /// Whether TEE isolation is enforced during reasoning.
    pub tee_enforced: bool,

    /// Whether PQC anchoring is enabled for reasoning trace.
    pub pqc_anchor: bool,
}

impl Default for SwiReasoningConfig {
    fn default() -> Self {
        Self {
            entropy_ref_x1000: 380,
            max_switches: 6,
            block_size: 64,
            latent_depth: 2,
            explicit_commit_threshold: 700,
            language_bias: LanguageBias::General,
            tee_enforced: true,
            pqc_anchor: true,
        }
    }
}

impl SwiReasoningConfig {
    /// Create config from language bias with domain-appropriate defaults.
    pub fn from_language_bias(bias: LanguageBias) -> Self {
        Self {
            entropy_ref_x1000: bias.default_entropy_ref_x1000(),
            max_switches: bias.default_max_switches(),
            block_size: 64,
            latent_depth: 3,
            explicit_commit_threshold: 750,
            language_bias: bias,
            tee_enforced: true,
            pqc_anchor: true,
        }
    }

    /// Returns the entropy reference as f64.
    pub fn entropy_ref(&self) -> f64 {
        self.entropy_ref_x1000 as f64 / 1000.0
    }

    /// Returns the explicit commit threshold as f64.
    pub fn explicit_commit(&self) -> f64 {
        self.explicit_commit_threshold as f64 / 1000.0
    }
}

// ============================================================
// INFERENCE ENGINE ENUM
// ============================================================

/// Inference engine variants for the Arkhe Cathedral ecosystem.
/// Extended from v12.10.1 (6 variants) to v12.10.3 (7 variants).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum InferenceEngine {
    /// Local WASM execution (no external dependency)
    LocalWasm,

    /// Kimi K2.6 (Moonshot AI, 1T/32B MoE, 262K context)
    KimiK26,

    /// Kimi K2.7 Code (Moonshot AI, 1T/32B MoE, 262K context, $4/M)
    /// Substrato 1104.1 — v12.10.1
    KimiK27Code,

    /// Claude Fable 5 (Anthropic)
    ClaudeFable5,

    /// GPT-5.5 (OpenAI)
    GPT55,

    /// Llama 4 Maverick (Meta)
    Llama4Maverick,

    /// Rio-3.5-Open-397B (IplanRIO/Prefeitura do Rio)
    /// Substrato 1104.2 — v12.10.3
    /// 397B total / 17B active, 1M context, MIT license, SwiReasoning native
    Rio35Open397B,
}

impl InferenceEngine {
    /// Returns the canonical Hugging Face model ID or API endpoint.
    pub fn model_id(&self) -> &'static str {
        match self {
            Self::LocalWasm => "arkhe://local/wasm",
            Self::KimiK26 => "https://api.moonshot.cn/v1/models/kimi-k2-6",
            Self::KimiK27Code => "https://api.moonshot.cn/v1/models/kimi-k2-7-code",
            Self::ClaudeFable5 => "https://api.anthropic.com/v1/models/claude-fable-5",
            Self::GPT55 => "https://api.openai.com/v1/models/gpt-5.5",
            Self::Llama4Maverick => "https://api.together.ai/v1/models/llama-4-maverick",
            Self::Rio35Open397B => "prefeitura-rio/Rio-3.5-Open-397B",
        }
    }

    /// Returns the SwiReasoning configuration for this engine.
    /// Rio-3.5 has native SwiReasoning; others use Arkhe cognitive overlay.
    pub fn swi_config(&self, domain: Option<Domain>) -> SwiReasoningConfig {
        let bias = domain.map(|d| d.language_bias()).unwrap_or(LanguageBias::General);

        match self {
            Self::Rio35Open397B => SwiReasoningConfig {
                // Native SwiReasoning — entropy thresholds calibrated
                // for Portuguese technical/legal domain (lusófono)
                entropy_ref_x1000: bias.default_entropy_ref_x1000(),
                max_switches: bias.default_max_switches(),
                block_size: 64,
                latent_depth: 3,
                explicit_commit_threshold: 750,
                language_bias: bias,
                tee_enforced: true,
                pqc_anchor: true,
            },
            Self::KimiK27Code => SwiReasoningConfig {
                entropy_ref_x1000: 380,
                max_switches: 6,
                block_size: 32,
                latent_depth: 2,
                explicit_commit_threshold: 700,
                language_bias: LanguageBias::General,
                tee_enforced: true,
                pqc_anchor: true,
            },
            _ => SwiReasoningConfig::from_language_bias(bias),
        }
    }

    /// Capability scoring for task routing (0.0–1.0).
    pub fn capability_score(&self, task: &Task) -> f64 {
        match (self, task.domain) {
            (Self::Rio35Open397B, Domain::PortugueseLegal) => 0.92,
            (Self::Rio35Open397B, Domain::PortugueseTechnical) => 0.90,
            (Self::Rio35Open397B, Domain::AgenticCoding) => 0.80,
            (Self::Rio35Open397B, Domain::MultimodalVision) => 0.78,
            (Self::Rio35Open397B, Domain::Mathematics) => 0.94,
            (Self::Rio35Open397B, Domain::STEM) => 0.88,
            (Self::Rio35Open397B, Domain::TemporalAnalysis) => 0.85,
            (Self::Rio35Open397B, Domain::PostQuantumSecurity) => 0.82,
            (Self::Rio35Open397B, Domain::BlockchainGovernance) => 0.87,
            (Self::KimiK27Code, Domain::Mathematics) => 0.95,
            (Self::KimiK27Code, Domain::AgenticCoding) => 0.85,
            (Self::KimiK27Code, Domain::PortugueseLegal) => 0.72,
            (Self::ClaudeFable5, Domain::ReasoningUltra) => 0.95,
            (Self::GPT55, Domain::ReasoningUltra) => 0.98,
            _ => 0.75,
        }
    }

    /// Cost per million output tokens (USD). Rio-3.5 = 0.0 (MIT license).
    pub fn cost_per_million(&self) -> f64 {
        match self {
            Self::LocalWasm => 0.0,
            Self::Rio35Open397B => 0.0,     // Infrastructure only
            Self::KimiK27Code => 4.0,
            Self::KimiK26 => 3.5,
            Self::ClaudeFable5 => 8.0,
            Self::GPT55 => 12.0,
            Self::Llama4Maverick => 1.2,
        }
    }

    /// Returns whether the engine requires trust-remote-code.
    /// SECURITY: Only Rio-3.5 currently requires this — mitigated by TEE + FIG.
    pub fn requires_trust_remote_code(&self) -> bool {
        matches!(self, Self::Rio35Open397B)
    }

    /// Returns the TEE enclave type required for secure execution.
    pub fn tee_requirement(&self) -> TEEContext {
        match self {
            Self::Rio35Open397B => TEEContext {
                enclave_type: EnclaveType::SGX2,
                attestation: AttestationMode::DCAP,
                hard_reset_crypto: true,  // FIG 1091.0 integration
                zeroize_on_anomaly: true,
            },
            _ => TEEContext {
                enclave_type: EnclaveType::SGX2,
                attestation: AttestationMode::DCAP,
                hard_reset_crypto: false,
                zeroize_on_anomaly: false,
            },
        }
    }

    /// Returns the maximum context length in tokens.
    pub fn max_context_length(&self) -> usize {
        match self {
            Self::LocalWasm => 32768,
            Self::KimiK26 | Self::KimiK27Code => 262_144,
            Self::ClaudeFable5 => 200_000,
            Self::GPT55 => 128_000,
            Self::Llama4Maverick => 256_000,
            Self::Rio35Open397B => 1_010_000, // 1M native
        }
    }

    /// Returns whether the engine supports multimodal (vision) input.
    pub fn supports_multimodal(&self) -> bool {
        matches!(self, Self::Rio35Open397B | Self::KimiK27Code | Self::ClaudeFable5 | Self::GPT55)
    }

    /// Returns whether the engine has native SwiReasoning.
    pub fn has_native_swir(&self) -> bool {
        matches!(self, Self::Rio35Open397B)
    }
}

// ============================================================
// ENGINE ROUTER
// ============================================================

/// Routes tasks to the optimal inference engine based on capability and cost.
pub struct EngineRouter;

impl EngineRouter {
    /// Select the best engine for a given task.
    /// Considers: capability score, cost, latency budget, TEE requirements.
    pub fn select(engines: &[InferenceEngine], task: &Task) -> Option<InferenceEngine> {
        let mut candidates: Vec<(InferenceEngine, f64)> = engines
            .iter()
            .map(|e| {
                let score = e.capability_score(task);
                let cost_penalty = e.cost_per_million() / 100.0; // Normalize
                let tee_ok = !task.requires_tee || e.tee_requirement().enclave_type == EnclaveType::SGX2;
                let ctx_ok = task.prompt.len() + task.max_tokens <= e.max_context_length();

                if !tee_ok || !ctx_ok {
                    (e.clone(), 0.0)
                } else {
                    (e.clone(), score - cost_penalty)
                }
            })
            .filter(|(_, s)| *s > 0.0)
            .collect();

        candidates.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        candidates.first().map(|(e, _)| e.clone())
    }
}
