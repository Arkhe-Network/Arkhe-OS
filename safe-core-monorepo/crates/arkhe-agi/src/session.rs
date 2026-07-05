//! Histórico de sessão — mantém estado entre turnos.

use arkhe_inference::{ChatMessage, ChatRole, TokenUsage};
use std::collections::VecDeque;

const MAX_HISTORY_TURNS: usize = 100;

/// Histórico de uma sessão de conversa.
#[derive(Debug, Clone)]
pub struct SessionHistory {
    session_id: String,
    messages: VecDeque<ChatMessage>,
    total_usage: TokenUsage,
    turn_count: u64,
}

impl SessionHistory {
    pub fn new(session_id: &str) -> Self {
        Self {
            session_id: session_id.to_string(),
            messages: VecDeque::with_capacity(MAX_HISTORY_TURNS),
            total_usage: TokenUsage::default(),
            turn_count: 0,
        }
    }

    pub fn session_id(&self) -> &str { &self.session_id }
    pub fn turn_count(&self) -> u64 { self.turn_count }
    pub fn total_usage(&self) -> &TokenUsage { &self.total_usage }
    pub fn messages(&self) -> &VecDeque<ChatMessage> { &self.messages }

    /// Adiciona uma mensagem ao histórico.
    pub fn push(&mut self, message: ChatMessage) {
        self.messages.push_back(message);
        if self.messages.len() > MAX_HISTORY_TURNS {
            self.messages.pop_front();
        }
    }

    /// Adiciona par usuário+assistente e acumula uso.
    pub fn push_turn(&mut self, user: &str, assistant: &str, usage: TokenUsage) {
        self.push(ChatMessage::user(user));
        self.push(ChatMessage::assistant(assistant));
        self.total_usage = self.total_usage.add(&usage);
        self.turn_count += 1;
    }

    /// Retorna todas as mensagens como vec (para InferenceRequest).
    pub fn to_vec(&self) -> Vec<ChatMessage> {
        self.messages.iter().cloned().collect()
    }

    /// Limpa o histórico mantendo o session_id.
    pub fn clear(&mut self) {
        self.messages.clear();
        self.total_usage = TokenUsage::default();
        self.turn_count = 0;
    }
}
