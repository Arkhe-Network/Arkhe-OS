//! Rate limiting com janela deslizante.
//! ✅ F9: Usa VecDeque com limpeza, não Vec crescendo infinitamente.

use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc, Duration};
use dashmap::DashMap;
use std::collections::VecDeque;
use std::sync::Arc;

/// Configuração de rate limit.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RateLimitConfig {
    /// Máximo de requisições por janela.
    pub max_requests: usize,
    /// Tamanho da janela em segundos.
    pub window_secs: u64,
    /// Máximo de tokens por janela.
    pub max_tokens: u64,
    /// Máximo de erros por janela antes de backoff.
    pub max_errors: usize,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            max_requests: 60,
            window_secs: 60,
            max_tokens: 100_000,
            max_errors: 10,
        }
    }
}

/// Estado de rate limit por principal (sessão, agente, etc).
#[derive(Debug, Default)]
struct RateLimitState {
    /// ✅ F9: Janela deslizante com tamanho fixo — não cresce infinitamente.
    request_times: VecDeque<DateTime<Utc>>,
    /// Tokens consumidos na janela atual.
    tokens_used: u64,
    /// Erros na janela atual.
    error_count: usize,
}

impl RateLimitState {
    fn new() -> Self {
        Self::default()
    }

    /// Remove timestamps fora da janela.
    fn prune(&mut self, window: Duration) {
        let cutoff = Utc::now() - window;
        while let Some(&front) = self.request_times.front() {
            if front < cutoff {
                self.request_times.pop_front();
            } else {
                break;
            }
        }
    }

    /// Adiciona uma requisição. Retorna true se permitida.
    fn try_record_request(&mut self, config: &RateLimitConfig, tokens: u64) -> RateLimitResult {
        let window = Duration::seconds(config.window_secs as i64);
        self.prune(window);

        if self.request_times.len() >= config.max_requests {
            return RateLimitResult::Rejected {
                reason: RejectReason::RequestLimit,
                retry_after_secs: 0,
            };
        }

        if self.tokens_used + tokens > config.max_tokens {
            return RateLimitResult::Rejected {
                reason: RejectReason::TokenBudget,
                retry_after_secs: 0,
            };
        }

        if self.error_count >= config.max_errors {
            return RateLimitResult::Rejected {
                reason: RejectReason::ErrorLimit,
                retry_after_secs: 60, // backoff
            };
        }

        self.request_times.push_back(Utc::now());
        self.tokens_used += tokens;
        RateLimitResult::Allowed
    }

    fn record_error(&mut self, config: &RateLimitConfig) {
        let window = Duration::seconds(config.window_secs as i64);
        self.prune(window);
        self.error_count += 1;
    }

    fn tokens_remaining(&self, config: &RateLimitConfig) -> u64 {
        config.max_tokens.saturating_sub(self.tokens_used)
    }
}

/// Resultado de uma verificação de rate limit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RateLimitResult {
    Allowed,
    Rejected { reason: RejectReason, retry_after_secs: u64 },
}

/// Razão da rejeição.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RejectReason {
    RequestLimit,
    TokenBudget,
    ErrorLimit,
}

/// Rate limiter global com suporte a múltiplos principals.
pub struct RateLimiter {
    config: RateLimitConfig,
    states: DashMap<String, RateLimitState>,
}

impl RateLimiter {
    pub fn new(config: RateLimitConfig) -> Self {
        Self {
            config,
            states: DashMap::new(),
        }
    }

    pub fn check(&self, principal: &str, tokens: u64) -> RateLimitResult {
        let mut state = self.states.entry(principal.to_string()).or_default();
        state.try_record_request(&self.config, tokens)
    }

    pub fn record_error(&self, principal: &str) {
        let mut state = self.states.entry(principal.to_string()).or_default();
        state.record_error(&self.config);
    }

    pub fn tokens_remaining(&self, principal: &str) -> u64 {
        self.states
            .get(principal)
            .map(|s| s.tokens_remaining(&self.config))
            .unwrap_or(self.config.max_tokens)
    }

    pub fn config(&self) -> &RateLimitConfig {
        &self.config
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new(RateLimitConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allows_within_limit() {
        let rl = RateLimiter::new(RateLimitConfig {
            max_requests: 3,
            window_secs: 60,
            max_tokens: 1000,
            max_errors: 5,
        });
        assert_eq!(rl.check("s1", 100), RateLimitResult::Allowed);
        assert_eq!(rl.check("s1", 100), RateLimitResult::Allowed);
        assert_eq!(rl.check("s1", 100), RateLimitResult::Allowed);
        assert!(matches!(rl.check("s1", 100), RateLimitResult::Rejected { .. }));
    }

    #[test]
    fn test_token_budget() {
        let rl = RateLimiter::new(RateLimitConfig {
            max_requests: 100,
            window_secs: 60,
            max_tokens: 500,
            max_errors: 5,
        });
        assert_eq!(rl.check("s1", 300), RateLimitResult::Allowed);
        assert!(matches!(rl.check("s1", 300), RateLimitResult::Rejected {
            reason: RejectReason::TokenBudget,
            ..
        }));
    }

    #[test]
    fn test_error_backoff() {
        let rl = RateLimiter::new(RateLimitConfig {
            max_requests: 100,
            window_secs: 60,
            max_tokens: 100000,
            max_errors: 2,
        });
        rl.record_error("s1");
        rl.record_error("s1");
        assert!(matches!(rl.check("s1", 10), RateLimitResult::Rejected {
            reason: RejectReason::ErrorLimit,
            retry_after_secs: 60,
        }));
    }

    #[test]
    fn test_separate_principals() {
        let rl = RateLimiter::new(RateLimitConfig {
            max_requests: 2,
            window_secs: 60,
            max_tokens: 10000,
            max_errors: 5,
        });
        assert_eq!(rl.check("a", 100), RateLimitResult::Allowed);
        assert_eq!(rl.check("a", 100), RateLimitResult::Allowed);
        assert!(matches!(rl.check("a", 100), RateLimitResult::Rejected { .. }));
        // Outro principal não é afetado
        assert_eq!(rl.check("b", 100), RateLimitResult::Allowed);
    }

    #[test]
    fn test_tokens_remaining() {
        let rl = RateLimiter::new(RateLimitConfig {
            max_tokens: 1000,
            ..Default::default()
        });
        assert_eq!(rl.tokens_remaining("s1"), 1000);
        rl.check("s1", 300);
        assert_eq!(rl.tokens_remaining("s1"), 700);
    }

    #[tokio::test]
    async fn test_concurrent_access() {
        let rl = Arc::new(RateLimiter::new(RateLimitConfig {
            max_requests: 10,
            window_secs: 60,
            max_tokens: 10000,
            max_errors: 5,
        }));

        let mut handles = Vec::new();
        for _ in 0..10 {
            let rl = rl.clone();
            handles.push(tokio::spawn(async move {
                rl.check("concurrent", 100)
            }));
        }

        for h in handles {
            let result = h.await.unwrap();
            assert_eq!(result, RateLimitResult::Allowed);
        }

        // 11th should be rejected
        assert!(matches!(
            rl.check("concurrent", 100),
            RateLimitResult::Rejected { .. }
        ));
    }
}
