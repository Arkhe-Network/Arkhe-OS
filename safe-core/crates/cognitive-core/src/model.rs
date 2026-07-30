//! Fábrica de Modelos: Suporte a Candle (nativo)
//!
//! APIs verificadas contra candle-core 0.11, candle-transformers 0.11

use candle_core::{Device, Tensor, DType};
use candle_nn::VarBuilder;
use candle_transformers::models::llama::{Llama, Config, Cache as LlamaCache};
use candle_transformers::generation::LogitsProcessor;
use hf_hub::{api::sync::Api, Repo, RepoType};
use tokenizers::Tokenizer;
use std::path::PathBuf;
use crate::error::CognitiveError;

/// Trait para backends de inferência de linguagem.
pub trait LanguageBackend: Send + Sync {
    /// Gera texto a partir de um prompt.
    fn generate(&mut self, prompt: &str, max_tokens: usize) -> Result<String, CognitiveError>;

    /// Gera embedding a partir de texto.
    /// Retorna NotImplemented se o backend não suportar embeddings.
    fn embed(&self, _text: &str) -> Result<Vec<f32>, CognitiveError> {
        Err(CognitiveError::Embedding(
            "Embeddings not supported by this backend".into()
        ))
    }
}

/// Backend Candle para inferência local de LLMs (Llama).
pub struct CandleBackend {
    model: Llama,
    tokenizer: Tokenizer,
    device: Device,
    config: candle_transformers::models::llama::LlamaConfig,
    logits_processor: LogitsProcessor,
}

impl CandleBackend {
    /// Carrega um modelo Llama do HuggingFace Hub.
    ///
    /// # Arguments
    /// * `model_id` — ID do modelo no HF Hub (ex: "meta-llama/Llama-2-7b-hf")
    /// * `revision` — Revisão/branch (ex: "main")
    pub fn new(model_id: &str, revision: &str) -> Result<Self, CognitiveError> {
        let api = Api::new().map_err(|e| CognitiveError::HfHub(e.to_string()))?;
        let repo = api.repo(Repo::with_revision(
            model_id.to_string(),
            RepoType::Model,
            revision.to_string(),
        ));

        // Carregar tokenizer
        let tokenizer_path = repo.get("tokenizer.json")
            .map_err(|e| CognitiveError::Tokenizer(format!("tokenizer: {}", e)))?;
        let tokenizer = Tokenizer::from_file(tokenizer_path)
            .map_err(|e| CognitiveError::Tokenizer(format!("tokenizer parse: {}", e)))?;

        // Carregar config
        let config_path = repo.get("config.json")
            .map_err(|e| CognitiveError::ModelLoad(format!("config: {}", e)))?;
        let config_str = std::fs::read_to_string(&config_path)?;
        let config: candle_transformers::models::llama::LlamaConfig = serde_json::from_str(&config_str)
            .map_err(|e| CognitiveError::ModelLoad(format!("config parse: {}", e)))?;

        let device = Device::new_cuda(0).unwrap_or(Device::Cpu);
        let dtype = DType::F16;

        // Carregar safetensors (descobrir dinamicamente)
        let mut filenames = Self::discover_safetensors(&repo)?;
        if filenames.is_empty() {
            return Err(CognitiveError::ModelLoad(
                "No safetensors files found".into()
            ));
        }

        let vb = unsafe {
            VarBuilder::from_mmaped_safetensors(&filenames, dtype, &device)
                .map_err(|e| CognitiveError::ModelLoad(format!("varbuilder: {}", e)))?
        };

        let model = Llama::load(vb, &config.clone().into_config(false))
            .map_err(|e| CognitiveError::ModelLoad(format!("model load: {}", e)))?;

        Ok(Self {
            model,
            tokenizer,
            device,
            config,
            logits_processor: LogitsProcessor::new(42, None, None),
        })
    }

    /// Descobre arquivos safetensors dinamicamente (lê index se existir).
    fn discover_safetensors(repo: &hf_hub::api::sync::ApiRepo) -> Result<Vec<PathBuf>, CognitiveError> {
        // Tentar ler index primeiro
        if let Ok(index_path) = repo.get("model.safetensors.index.json") {
            let index_str = std::fs::read_to_string(&index_path)?;
            let index: serde_json::Value = serde_json::from_str(&index_str)?;

            if let Some(weight_map) = index.get("weight_map").and_then(|m| m.as_object()) {
                let mut seen = std::collections::HashSet::new();
                let mut filenames = Vec::new();
                for filename in weight_map.values() {
                    if let Some(name) = filename.as_str() {
                        if seen.insert(name.to_string()) {
                            let path = repo.get(name)
                                .map_err(|e| CognitiveError::HfHub(format!("{}: {}", name, e)))?;
                            filenames.push(path);
                        }
                    }
                }
                return Ok(filenames);
            }
        }

        // Fallback: procurar model.safetensors único
        if let Ok(path) = repo.get("model.safetensors") {
            return Ok(vec![path]);
        }

        Ok(Vec::new())
    }
}

impl LanguageBackend for CandleBackend {
    fn generate(&mut self, prompt: &str, max_tokens: usize) -> Result<String, CognitiveError> {
        let encoding = self.tokenizer.encode(prompt, true)
            .map_err(|e| CognitiveError::Tokenizer(e.to_string()))?;
        let mut tokens = encoding.get_ids().to_vec();
        let eos_token = self.tokenizer.token_to_id("</s>");

        // Usar Cache mutável (não clone a cada iteração)
        let mut cache = LlamaCache::new(true, DType::F16, &self.config.clone().into_config(false), &self.device)?;

        for _ in 0..max_tokens {
            let start_idx = tokens.len().saturating_sub(512);
            let input = Tensor::new(&tokens[start_idx..], &self.device)?
                .unsqueeze(0)?;

            let logits = self.model.forward(&input, tokens.len() - start_idx, &mut cache)?
                .squeeze(0)?;

            let next_token = self.logits_processor.sample(&logits)?;
            tokens.push(next_token);

            if Some(next_token) == eos_token {
                break;
            }
        }

        let decoded = self.tokenizer.decode(&tokens, true)
            .map_err(|e| CognitiveError::Tokenizer(e.to_string()))?;

        Ok(decoded)
    }
}

/// Backend para geração de embeddings (MiniLM/Sentence-BERT via Candle).
pub struct EmbeddingBackend {
    // Placeholder: requer modelo de embeddings separado
    dimension: usize,
}

impl EmbeddingBackend {
    pub fn new(dimension: usize) -> Self {
        Self { dimension }
    }

    /// Gera embedding dummy para testes.
    /// Em produção, carregaria sentence-transformers/all-MiniLM-L6-v2 via Candle.
    pub fn embed_dummy(&self, text: &str) -> Vec<f32> {
        // Hash determinístico do texto para embedding dummy
        use sha2::{Sha256, Digest};
        let hash = Sha256::digest(text.as_bytes());
        let mut embedding = Vec::with_capacity(self.dimension);
        for i in 0..self.dimension {
            let byte = hash[i % hash.len()];
            embedding.push((byte as f32 / 255.0) * 2.0 - 1.0);
        }
        embedding
    }
}

/// Registro de modelos carregados.
pub struct ModelRegistry {
    pub language_backend: Option<Box<dyn LanguageBackend>>,
    pub embedding_backend: Option<EmbeddingBackend>,
}

impl ModelRegistry {
    pub fn new() -> Self {
        Self {
            language_backend: None,
            embedding_backend: None,
        }
    }

    pub fn register_language_backend(&mut self, backend: Box<dyn LanguageBackend>) {
        self.language_backend = Some(backend);
    }

    pub fn register_embedding_backend(&mut self, backend: EmbeddingBackend) {
        self.embedding_backend = Some(backend);
    }
}

impl Default for ModelRegistry {
    fn default() -> Self {
        Self::new()
    }
}
