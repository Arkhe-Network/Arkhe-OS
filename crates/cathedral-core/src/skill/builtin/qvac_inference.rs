use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QVACConfig {
    pub context_size: usize,
    pub threads: usize,
    pub temperature: f32,
    pub top_p: f32,
    pub max_tokens: usize,
}

impl Default for QVACConfig {
    fn default() -> Self {
        Self {
            context_size: 4096,
            threads: 4,
            temperature: 0.7,
            top_p: 0.9,
            max_tokens: 1024,
        }
    }
}

pub struct QVACSession {
    model_path: PathBuf,
    config: QVACConfig,
}

impl QVACSession {
    pub async fn new(model_data: &[u8], config: QVACConfig) -> Result<Self, String> {
        let temp_dir = std::env::temp_dir().join("qvac_models");
        std::fs::create_dir_all(&temp_dir)
            .map_err(|e| format!("Erro ao criar diretório temporário: {}", e))?;

        let model_path = temp_dir.join(format!("model_{}.gguf", uuid::Uuid::new_v4()));
        std::fs::write(&model_path, model_data)
            .map_err(|e| format!("Erro ao escrever modelo: {}", e))?;

        tracing::info!("✅ Sessão QVAC inicializada: {}", model_path.display());

        Ok(Self { model_path, config })
    }

    pub async fn infer(&self, prompt: &str) -> Result<String, String> {
        tracing::info!("🧠 [QVAC] Inferindo localmente...");
        tokio::time::sleep(tokio::time::Duration::from_millis(150)).await;
        Ok(format!("[QVAC Local] {}", &prompt[..prompt.len().min(80)]))
    }
}

impl Drop for QVACSession {
    fn drop(&mut self) {
        if self.model_path.exists() {
            let _ = std::fs::remove_file(&self.model_path);
        }
    }
}

pub struct QVACInferenceExecutor {
    // storage: HashTreeStorage, // simulated
    config: QVACConfig,
    session_cache: Arc<Mutex<Option<QVACSession>>>,
    default_model_hash: String,
}

impl QVACInferenceExecutor {
    pub fn new(
        config: QVACConfig,
        default_model_hash: &str,
    ) -> Self {
        Self {
            config,
            session_cache: Arc::new(Mutex::new(None)),
            default_model_hash: default_model_hash.to_string(),
        }
    }

    pub async fn infer(
        &self,
        prompt: &str,
        model_hash: Option<&str>,
        _trace_id: Option<&str>,
    ) -> Result<String, String> {
        let _model_hash = model_hash.unwrap_or(&self.default_model_hash);

        let mut cache = self.session_cache.lock().await;

        let session = match cache.as_mut() {
            Some(s) => s,
            None => {
                let model_data = vec![0, 1, 2, 3]; // mock hash tree fetch
                let new_session = QVACSession::new(&model_data, self.config.clone()).await?;
                *cache = Some(new_session);
                cache.as_mut().unwrap()
            }
        };

        let result = session.infer(prompt).await?;

        Ok(result)
    }
}
