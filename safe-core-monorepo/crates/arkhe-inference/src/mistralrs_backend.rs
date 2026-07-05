//! Backend Mistral.rs — implementação real usando a API do crate mistralrs.
//!
//! Ativado com: `cargo check -p arkhe-inference --features mistralrs-backend`

use async_trait::async_trait;
use chrono::Utc;
use tokio::sync::mpsc;
use tracing::{info, warn, error, debug};

use crate::{
    InferenceEngine, InferenceRequest, InferenceResponse, InferenceResult,
    ModelId, ModelCapabilities, FinishReason, TokenUsage, StreamChunk,
    ChatMessage, ChatRole,
};
use crate::error::InferenceError;

/// Wrapper em torno do motor Mistral.rs.
pub struct MistralRsEngine {
    model_id: ModelId,
    pipeline: std::sync::Arc<tokio::sync::RwLock<Option<mistralrs::Pipeline>>>,
    model_path: String,
    capabilities: ModelCapabilities,
}

impl MistralRsEngine {
    /// Cria um novo engine Mistral.rs sem carregar modelo.
    pub fn new(model_id: ModelId, model_path: String) -> Self {
        Self {
            model_id,
            pipeline: std::sync::Arc::new(tokio::sync::RwLock::new(None)),
            model_path,
            capabilities: ModelCapabilities {
                chat: true,
                completion: true,
                tools: true,
                vision: false,
                streaming: true,
                max_context_tokens: 32768,
            },
        }
    }

    /// Carrega o modelo (lazy loading).
    pub async fn load(&self) -> InferenceResult<()> {
        let mut pipeline = self.pipeline.write().await;
        if pipeline.is_some() {
            return Ok(()); // Já carregado
        }

        info!(model = %self.model_id, path = %self.model_path, "Loading Mistral.rs model");

        let scheduler_config = mistralrs::SchedulerConfig {
            // Usar GPU se disponível, senão CPU
            ..Default::default()
        };

        let model_source = mistralrs::NormalRequest {
            model_id: self.model_id.as_str().to_string(),
            tokenizer_json: None,
            tokenizer_config: None,
            filenames: vec![self.model_path.clone()],
            arch: None,
        };

        let loader = mistralrs::Loader {
            model_source: mistralrs::ModelSource::Normal(model_source),
            config: mistralrs::Config::default(),
            scheduling: scheduler_config,
        };

        match mistralrs::Pipeline::new(loader) {
            Ok(p) => {
                info!(model = %self.model_id, "Model loaded successfully");
                *pipeline = Some(p);
                Ok(())
            }
            Err(e) => {
                error!(model = %self.model_id, error = %e, "Failed to load model");
                Err(InferenceError::LoadFailed(format!("{}", e)))
            }
        }
    }

    /// Verifica se o modelo está carregado e carrega se necessário.
    async fn ensure_loaded(&self) -> InferenceResult<()> {
        let pipeline = self.pipeline.read().await;
        if pipeline.is_some() {
            return Ok(());
        }
        drop(pipeline);
        self.load().await
    }
}

/// Converte ChatMessage do Arkhe para o formato do Mistral.rs.
fn to_mistral_messages(messages: &[ChatMessage]) -> Vec<mistralrs::RequestMessage> {
    messages.iter().map(|m| {
        match m.role {
            ChatRole::System => mistralrs::RequestMessage::System {
                content: mistralrs::Content::Text(m.content.clone()),
            },
            ChatRole::User => mistralrs::RequestMessage::User {
                content: mistralrs::Content::Text(m.content.clone()),
            },
            ChatRole::Assistant => {
                let tool_calls = if m.tool_calls.is_empty() {
                    None
                } else {
                    Some(m.tool_calls.iter().map(|tc| {
                        mistralrs::ToolCall {
                            id: tc.id.clone(),
                            name: tc.name.clone(),
                            arguments: tc.arguments.to_string(),
                        }
                    }).collect())
                };
                mistralrs::RequestMessage::Assistant {
                    content: Some(mistralrs::Content::Text(m.content.clone())),
                    tool_calls,
                }
            },
            ChatRole::Tool => mistralrs::RequestMessage::Tool {
                content: mistralrs::Content::Text(m.content.clone()),
                name: m.name.clone().unwrap_or_default(),
                id: String::new(), // Tool ID seria passado via metadata
            },
        }
    }).collect()
}

#[async_trait]
impl InferenceEngine for MistralRsEngine {
    fn model_id(&self) -> &ModelId { &self.model_id }

    async fn complete(&self, request: InferenceRequest) -> InferenceResult<InferenceResponse> {
        self.ensure_loaded().await?;

        let pipeline = self.pipeline.read().await;
        let pipeline = pipeline.as_ref().ok_or(InferenceError::NotReady {
            model_id: self.model_id.clone(),
        })?;

        let mistral_messages = to_mistral_messages(&request.messages);

        // Construir sampling params
        let sampling = mistralrs::SamplingParams {
            temperature: Some(request.params.temperature),
            top_k: Some(request.params.top_k as usize),
            top_p: Some(request.params.top_p),
            max_tokens: Some(request.params.max_tokens as usize),
            ..Default::default()
        };

        let request_body = mistralrs::Request {
            messages: mistral_messages,
            sampling,
            tools: if request.tools.is_empty() {
                None
            } else {
                Some(request.tools.iter().map(|t| {
                    mistralrs::ToolDefinition {
                        name: t.name.clone(),
                        description: t.description.clone(),
                        parameters: t.parameters.clone(),
                    }
                }).collect())
            },
            ..Default::default()
        };

        let start = std::time::Instant::now();

        match pipeline.send_chat_request(request_body).await {
            Ok(response) => {
                let duration = start.elapsed();
                debug!(
                    model = %self.model_id,
                    duration_ms = duration.as_millis(),
                    "Inference completed"
                );

                let content = response.choices
                    .first()
                    .and_then(|c| c.message.content.clone())
                    .unwrap_or_default();

                let finish_reason = response.choices
                    .first()
                    .map(|c| match c.finish_reason.as_str() {
                        "stop" => FinishReason::Stop,
                        "length" => FinishReason::Length,
                        "tool_calls" => FinishReason::ToolCall,
                        _ => FinishReason::Error,
                    })
                    .unwrap_or(FinishReason::Stop);

                let usage = response.usage.as_ref().map(|u| {
                    TokenUsage::new(
                        u.prompt_tokens as u32,
                        u.completion_tokens as u32,
                    )
                }).unwrap_or_default();

                let tool_calls = response.choices
                    .first()
                    .and_then(|c| c.message.tool_calls.as_ref())
                    .map(|tcs| {
                        tcs.iter().map(|tc| crate::ToolCall {
                            id: tc.id.clone(),
                            name: tc.name.clone(),
                            arguments: serde_json::from_str(&tc.arguments)
                                .unwrap_or(serde_json::Value::Null),
                        }).collect()
                    })
                    .unwrap_or_default();

                Ok(InferenceResponse {
                    content,
                    tool_calls,
                    usage,
                    finish_reason,
                    timestamp: Utc::now(),
                    metadata: std::collections::HashMap::new(),
                })
            }
            Err(e) => {
                error!(model = %self.model_id, error = %e, "Inference failed");
                Err(InferenceError::InferenceFailed(e.to_string()))
            }
        }
    }

    async fn stream(&self, request: InferenceRequest) -> InferenceResult<mpsc::Receiver<StreamChunk>> {
        self.ensure_loaded().await?;

        let pipeline = self.pipeline.read().await;
        let pipeline = pipeline.as_ref().ok_or(InferenceError::NotReady {
            model_id: self.model_id.clone(),
        })?;

        let mistral_messages = to_mistral_messages(&request.messages);
        let sampling = mistralrs::SamplingParams {
            temperature: Some(request.params.temperature),
            top_k: Some(request.params.top_k as usize),
            top_p: Some(request.params.top_p),
            max_tokens: Some(request.params.max_tokens as usize),
            ..Default::default()
        };

        let request_body = mistralrs::Request {
            messages: mistral_messages,
            sampling,
            tools: None,
            ..Default::default()
        };

        let (tx, rx) = mpsc::channel(64);

        let model_id_str = self.model_id.as_str();
        tokio::spawn(async move {
            match pipeline.send_chat_request_streaming(request_body).await {
                Ok(receiver) => {
                    // O receiver do mistralrs implementa Stream
                    use futures::StreamExt;
                    let mut stream = receiver;
                    while let Some(result) = stream.next().await {
                        match result {
                            Ok(chunk) => {
                                let token = chunk.choices
                                    .first()
                                    .and_then(|c| c.delta.content.clone())
                                    .unwrap_or_default();

                                let finish = chunk.choices.first().and_then(|c| {
                                    if c.finish_reason.is_empty() { None }
                                    else {
                                        Some(match c.finish_reason.as_str() {
                                            "stop" => FinishReason::Stop,
                                            "length" => FinishReason::Length,
                                            "tool_calls" => FinishReason::ToolCall,
                                            _ => FinishReason::Error,
                                        })
                                    }
                                });

                                let stream_chunk = StreamChunk {
                                    token,
                                    finish_reason: finish,
                                    timestamp: Utc::now(),
                                };

                                if tx.send(stream_chunk).await.is_err() {
                                    break; // Consumer desconectou
                                }
                            }
                            Err(e) => {
                                warn!(model = model_id_str, error = %e, "Stream error");
                                let _ = tx.send(StreamChunk {
                                    token: String::new(),
                                    finish_reason: Some(FinishReason::Error),
                                    timestamp: Utc::now(),
                                }).await;
                                break;
                            }
                        }
                    }
                }
                Err(e) => {
                    error!(model = model_id_str, error = %e, "Failed to start stream");
                    let _ = tx.send(StreamChunk {
                        token: String::new(),
                        finish_reason: Some(FinishReason::Error),
                        timestamp: Utc::now(),
                    }).await;
                }
            }
        });

        Ok(rx)
    }

    fn is_ready(&self) -> bool {
        let pipeline = self.pipeline.try_read();
        pipeline.map(|p| p.is_some()).unwrap_or(false)
    }

    fn max_context_tokens(&self) -> u32 {
        self.capabilities.max_context_tokens
    }
}
