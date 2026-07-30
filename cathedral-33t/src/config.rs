use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CathedralConfig {
    pub model: ModelConfig,
    pub training: TrainingConfig,
    pub inference: InferenceConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    pub hidden_size: usize,
    pub num_layers: usize,
    pub vocab_size: usize,
    pub max_seq_len: usize,
    pub moe: MoEConfig,
    pub attention: AttentionConfig,
    pub mhc_expansion_rate: usize,
    pub quantization: QuantizationConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoEConfig {
    pub num_experts: usize,
    pub top_k: usize,
    pub hidden_size: usize,
    pub intermediate_size: usize,
    pub capacity_factor: f32,
    pub load_balancing_loss_coef: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AttentionConfig {
    pub num_heads: usize,
    pub head_dim: usize,
    pub csa_compression: usize,
    pub hca_compression: usize,
    pub sliding_window_size: usize,
    pub mla_latent_dim: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuantizationConfig {
    pub weight_precision: String,
    pub activation_precision: String,
    pub router_precision: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingConfig {
    pub total_steps: u64,
    pub batch_size: usize,
    pub learning_rate: f64,
    pub optimizer: String,
    pub warmup_steps: u64,
    pub gradient_clip_norm: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceConfig {
    pub speculative_tokens: usize,
    pub draft_model_path: String,
    pub batch_size: usize,
    pub quantize: bool,
}
