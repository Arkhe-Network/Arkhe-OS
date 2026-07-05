use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ─── Request ────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceRequest {
    pub messages: Vec<ChatMessage>,
    pub params: SamplingParams,
    #[serde(default)]
    pub tools: Vec<ToolDefinition>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

impl InferenceRequest {
    /// Construtor simples — única mensagem de usuário.
    pub fn simple(prompt: &str) -> Self {
        Self {
            messages: vec![ChatMessage::user(prompt)],
            params: SamplingParams::default(),
            tools: Vec::new(),
            session_id: None,
        }
    }

    /// Construtor com sistema + usuário.
    pub fn with_system(system: &str, user: &str) -> Self {
        Self {
            messages: vec![ChatMessage::system(system), ChatMessage::user(user)],
            params: SamplingParams::default(),
            tools: Vec::new(),
            session_id: None,
        }
    }
}

// ─── Message ────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: ChatRole,
    pub content: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tool_calls: Vec<ToolCall>,
}

impl ChatMessage {
    pub fn system(content: &str) -> Self {
        Self { role: ChatRole::System, content: content.to_string(), name: None, tool_calls: Vec::new() }
    }
    pub fn user(content: &str) -> Self {
        Self { role: ChatRole::User, content: content.to_string(), name: None, tool_calls: Vec::new() }
    }
    pub fn assistant(content: &str) -> Self {
        Self { role: ChatRole::Assistant, content: content.to_string(), name: None, tool_calls: Vec::new() }
    }
    pub fn tool(name: &str, content: &str, call_id: &str) -> Self {
        Self { role: ChatRole::Tool, content: content.to_string(), name: Some(name.to_string()), tool_calls: Vec::new() }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ChatRole {
    System,
    User,
    Assistant,
    Tool,
}

// ─── Sampling ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SamplingParams {
    #[serde(default = "default_temperature")]
    pub temperature: f32,
    #[serde(default = "default_top_p")]
    pub top_p: f32,
    #[serde(default = "default_top_k")]
    pub top_k: u32,
    #[serde(default = "default_max_tokens")]
    pub max_tokens: u32,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub stop_sequences: Vec<String>,
    #[serde(default)]
    pub stream: bool,
}

fn default_temperature() -> f32 { 0.7 }
fn default_top_p() -> f32 { 0.9 }
fn default_top_k() -> u32 { 40 }
fn default_max_tokens() -> u32 { 4096 }

impl Default for SamplingParams {
    fn default() -> Self {
        Self {
            temperature: default_temperature(),
            top_p: default_top_p(),
            top_k: default_top_k(),
            max_tokens: default_max_tokens(),
            stop_sequences: Vec::new(),
            stream: false,
        }
    }
}

// ─── Tools ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub parameters: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: String,
    pub name: String,
    pub arguments: serde_json::Value,
}

// ─── Response ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceResponse {
    pub content: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tool_calls: Vec<ToolCall>,
    pub usage: TokenUsage,
    pub finish_reason: FinishReason,
    pub timestamp: DateTime<Utc>,
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, String>,
}

// ─── Streaming ──────────────────────────────────────────────────────────────

/// Evento de streaming — enviado token a token.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StreamChunk {
    pub token: String,
    pub finish_reason: Option<FinishReason>,
    pub timestamp: DateTime<Utc>,
}

/// Eventos possíveis durante streaming.
#[derive(Debug, Clone)]
pub enum StreamEvent {
    /// Token recebido.
    Token(String),
    /// Streaming completo.
    Done(FinishReason),
    /// Erro durante streaming.
    Error(String),
}

// ─── TokenUsage ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct TokenUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

impl TokenUsage {
    pub fn new(prompt_tokens: u32, completion_tokens: u32) -> Self {
        Self {
            prompt_tokens,
            completion_tokens,
            total_tokens: prompt_tokens + completion_tokens,
        }
    }

    pub fn is_zero(&self) -> bool {
        self.total_tokens == 0
    }

    pub fn add(&self, other: &Self) -> Self {
        Self {
            prompt_tokens: self.prompt_tokens + other.prompt_tokens,
            completion_tokens: self.completion_tokens + other.completion_tokens,
            total_tokens: self.total_tokens + other.total_tokens,
        }
    }

    /// Zera os contadores (útil para reset entre turnos).
    pub fn reset(&self) -> Self {
        Self::default()
    }
}

impl std::fmt::Display for TokenUsage {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}+{}={}", self.prompt_tokens, self.completion_tokens, self.total_tokens)
    }
}

// ─── FinishReason ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FinishReason {
    Stop,
    Length,
    ToolCall,
    Error,
}

impl std::fmt::Display for FinishReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Stop => write!(f, "stop"),
            Self::Length => write!(f, "length"),
            Self::ToolCall => write!(f, "tool_call"),
            Self::Error => write!(f, "error"),
        }
    }
}
