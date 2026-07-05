//! AgiCoordinator — Orquestrador central DESACOPLADO.
//!
//! Usa traits de arkhe-core (SafetyVerifier, AgentMemory) em vez de
//! depender de arkhe-pea e arkhe-memory diretamente. Isso permite:
//! - Testar com AlwaysAllowVerifier + InMemoryAgentMemory
//! - Trocar implementações sem recompilar
//! - Eliminar dependências circulares

use arkhe_core::{
    ArkheResult, SafetyVerifier, SafetyVerdict, AgentMemory, MemoryEntry, MemoryLayer,
};
use arkhe_inference::{
    InferenceEngine, InferenceRequest, InferenceResponse, ChatMessage, ChatRole, FinishReason,
};
use arkhe_session_evaluator::{SessionTrajectory, SessionEvaluator};
use arkhe_reflector_agent::ReflectorAgent;
use crate::session::SessionHistory;
use std::sync::Arc;
use tracing::{info, warn, error};

/// Coordenador AGI — ponto central de orquestração.
///
/// Genérico sobre 3 componentes:
/// - `V`: Verificador de segurança (ex: SafetyEnforcer do PEA, ou AlwaysAllowVerifier para dev)
/// - `M`: Memória do agente (ex: EvolutionaryMemory, ou InMemoryAgentMemory para testes)
/// - `I`: Motor de inferência (ex: MistralRsEngine, NullEngine, etc.)
pub struct AgiCoordinator<V, M, I>
where
    V: SafetyVerifier,
    M: AgentMemory,
    I: InferenceEngine,
{
    safety: Arc<V>,
    memory: Arc<M>,
    inference: Arc<I>,
    evaluator: Arc<SessionEvaluator>,
    history: tokio::sync::RwLock<SessionHistory>,
    system_prompt: String,
}

impl<V, M, I> AgiCoordinator<V, M, I>
where
    V: SafetyVerifier,
    M: AgentMemory,
    I: InferenceEngine,
{
    /// Cria um novo coordenador.
    pub fn new(
        safety: Arc<V>,
        memory: Arc<M>,
        inference: Arc<I>,
        evaluator: Arc<SessionEvaluator>,
        session_id: &str,
        system_prompt: &str,
    ) -> Self {
        Self {
            safety,
            memory,
            inference,
            evaluator,
            history: tokio::sync::RwLock::new(SessionHistory::new(session_id)),
            system_prompt: system_prompt.to_string(),
        }
    }

    /// Processa input do usuário com ciclo completo.
    ///
    /// Fluxo:
    /// 1. Verificar segurança
    /// 2. Construir requisição (histórico + novo input)
    /// 3. Executar inferência
    /// 4. Armazenar na memória
    /// 5. Atualizar histórico
    pub async fn process(&self, user_input: &str) -> ArkheResult<String> {
        let start = std::time::Instant::now();
        let session_id = {
            let h = self.history.read().await;
            h.session_id().to_string()
        };

        info!(session = %session_id, "Processing input");

        // 1. Verificação de segurança
        let verdict = self.safety.verify("llm_inference", user_input).await;
        if let SafetyVerdict::Rejected(reason) = verdict {
            warn!(session = %session_id, reason = %reason, "Safety rejected");
            return Err(arkhe_core::ArkheError::PermissionDenied(reason));
        }

        // 2. Construir requisição com histórico
        let mut messages = vec![ChatMessage::system(&self.system_prompt)];
        {
            let h = self.history.read().await;
            messages.extend(h.to_vec());
        }
        messages.push(ChatMessage::user(user_input));

        let request = InferenceRequest {
            messages,
            params: arkhe_inference::SamplingParams::default(),
            tools: Vec::new(),
            session_id: Some(session_id.clone()),
        };

        // 3. Inferência
        let response = self.inference.complete(request).await
            .map_err(|e| arkhe_core::ArkheError::Internal(e.to_string()))?;

        // 4. Armazenar na memória
        let now = chrono::Utc::now();
        let turn_key = format!("{}:turn-{}", session_id, now.timestamp_millis());

        let working_entry = MemoryEntry {
            key: turn_key.clone(),
            value: format!("User: {}\nAssistant: {}", user_input, response.content),
            score: if response.finish_reason == FinishReason::Stop { 0.9 } else { 0.5 },
            layer: MemoryLayer::Working,
            timestamp: now,
        };
        if let Err(e) = self.memory.store(working_entry).await {
            warn!(error = %e, "Failed to store in working memory");
        }

        let episode_entry = MemoryEntry {
            key: format!("{}:ep:{}", session_id, uuid::Uuid::new_v4()),
            value: format!("Query: {}", user_input),
            score: 0.7,
            layer: MemoryLayer::Episodic,
            timestamp: now,
        };
        if let Err(e) = self.memory.store(episode_entry).await {
            warn!(error = %e, "Failed to store in episodic memory");
        }

        // 5. Atualizar histórico
        {
            let mut h = self.history.write().await;
            h.push_turn(user_input, &response.content, response.usage);
        }

        let duration = start.elapsed();
        info!(
            session = %session_id,
            duration_ms = duration.as_millis(),
            tokens = response.usage.total_tokens,
            "Response generated"
        );

        Ok(response.content)
    }

    /// Avalia a sessão atual.
    pub async fn evaluate_session(&self) -> ArkheResult<arkhe_session_evaluator::EvaluationResult> {
        let h = self.history.read().await;
        let trajectory = SessionTrajectory {
            id: h.session_id().to_string(),
            agent_did: "arkhe:agi".to_string(),
            turns: h.messages().iter().enumerate().map(|(i, m)| {
                arkhe_session_evaluator::Turn {
                    id: format!("t{}", i),
                    role: match m.role {
                        ChatRole::System => arkhe_session_evaluator::TurnRole::System,
                        ChatRole::User => arkhe_session_evaluator::TurnRole::User,
                        ChatRole::Assistant => arkhe_session_evaluator::TurnRole::Assistant,
                        ChatRole::Tool => arkhe_session_evaluator::TurnRole::Tool,
                    },
                    content: m.content.clone(),
                    timestamp: chrono::Utc::now(),
                    reasoning: None,
                    validation: None,
                    artifacts: Vec::new(),
                    confidence: None,
                    causal_links: Vec::new(),
                }
            }).collect(),
            artifacts: Vec::new(),
            start_time: chrono::Utc::now(),
            end_time: Some(chrono::Utc::now()),
            metadata: std::collections::HashMap::new(),
        };
        drop(h);

        Ok(self.evaluator.evaluate(&trajectory).await)
    }

    /// Retorna estatísticas da sessão.
    pub async fn stats(&self) -> (String, u64, arkhe_inference::TokenUsage) {
        let h = self.history.read().await;
        (h.session_id().to_string(), h.turn_count(), *h.total_usage())
    }
}
