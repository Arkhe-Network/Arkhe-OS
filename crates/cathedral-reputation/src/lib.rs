use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;

/// Estrutura de dados de reputação para um agente.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReputationData {
    pub did: String,
    pub score: f64, // 0..100
    pub successes: u64,
    pub failures: u64,
    pub last_updated: i64,
}

/// Router de reputação com valores fixos e thresholds.
pub struct ReputationRouter {
    store: Arc<DashMap<String, ReputationData>>,
    thresholds: ReputationThresholds,
    fixed_mode: bool,
}

/// Thresholds para classificação de reputação.
#[derive(Debug, Clone, Copy)]
pub struct ReputationThresholds {
    pub excellent: f64, // ≥ 90
    pub good: f64,      // ≥ 70
    pub regular: f64,   // ≥ 50
    pub low: f64,       // ≥ 30
}

impl Default for ReputationThresholds {
    fn default() -> Self {
        Self {
            excellent: 90.0,
            good: 70.0,
            regular: 50.0,
            low: 30.0,
        }
    }
}

#[derive(Debug, Error)]
pub enum ReputationError {
    #[error("Agent not found")]
    NotFound,
    #[error("Invalid score")]
    InvalidScore,
}

impl ReputationRouter {
    /// Cria um novo router com dados fixos para protótipo.
    pub fn new() -> Self {
        let store = Arc::new(DashMap::new());
        // Dados fixos para os agentes do protótipo
        let fixed_data = vec![
            ("did:cathedral:agent:cathedral-llm-proto-001", 85.0, 10, 0),
            ("did:cathedral:agent:alpha", 90.0, 20, 1),
            ("did:cathedral:agent:beta", 70.0, 8, 2),
            ("did:cathedral:agent:gamma", 55.0, 5, 3),
            ("did:cathedral:agent:delta", 30.0, 1, 5),
        ];
        for (did, score, successes, failures) in fixed_data {
            store.insert(
                did.to_string(),
                ReputationData {
                    did: did.to_string(),
                    score,
                    successes,
                    failures,
                    last_updated: chrono::Utc::now().timestamp(),
                },
            );
        }
        Self {
            store,
            thresholds: ReputationThresholds::default(),
            fixed_mode: true,
        }
    }

    /// Obtém a pontuação de reputação de um agente.
    pub async fn score(&self, did: &str) -> Result<f64, ReputationError> {
        if self.fixed_mode {
            Ok(self.store.get(did).map(|entry| entry.score).unwrap_or(50.0))
        } else {
            // Modo dinâmico (futuro): calcular baseado em histórico
            Ok(50.0)
        }
    }

    /// Classifica uma pontuação de reputação.
    pub fn classify(&self, score: f64) -> &'static str {
        if score >= self.thresholds.excellent {
            "Excellent"
        } else if score >= self.thresholds.good {
            "Good"
        } else if score >= self.thresholds.regular {
            "Regular"
        } else if score >= self.thresholds.low {
            "Low"
        } else {
            "Critical"
        }
    }

    /// Atualiza a reputação de um agente (sucesso ou falha).
    pub async fn update(&self, did: &str, success: bool) -> Result<(), ReputationError> {
        let mut entry = self
            .store
            .entry(did.to_string())
            .or_insert_with(|| ReputationData {
                did: did.to_string(),
                score: 50.0,
                successes: 0,
                failures: 0,
                last_updated: chrono::Utc::now().timestamp(),
            });
        if success {
            entry.successes += 1;
            entry.score = (entry.score + 1.0).min(100.0);
        } else {
            entry.failures += 1;
            entry.score = (entry.score - 2.0).max(0.0);
        }
        entry.last_updated = chrono::Utc::now().timestamp();
        Ok(())
    }

    /// Retorna os thresholds atuais.
    pub fn thresholds(&self) -> ReputationThresholds {
        self.thresholds
    }
}
