use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CircuitState {
    Closed,     // Normal: requisições passam
    Open,       // Falha: requisições são bloqueadas
    HalfOpen,   // Teste: uma requisição passa para verificar recuperação
}

pub struct CircuitBreaker {
    state: Arc<Mutex<CircuitState>>,
    failure_count: AtomicUsize,
    success_count: AtomicUsize,
    config: CircuitBreakerConfig,
    last_state_change: Arc<Mutex<Instant>>,
}

#[derive(Debug, Clone)]
pub struct CircuitBreakerConfig {
    pub failure_threshold: usize,    // número de falhas para abrir
    pub success_threshold: usize,    // número de sucessos para fechar (HalfOpen)
    pub timeout_secs: u64,           // tempo para passar de Open para HalfOpen
}

impl Default for CircuitBreakerConfig {
    fn default() -> Self {
        Self {
            failure_threshold: 5,
            success_threshold: 2,
            timeout_secs: 30,
        }
    }
}

impl CircuitBreaker {
    pub fn new(config: CircuitBreakerConfig) -> Self {
        Self {
            state: Arc::new(Mutex::new(CircuitState::Closed)),
            failure_count: AtomicUsize::new(0),
            success_count: AtomicUsize::new(0),
            config,
            last_state_change: Arc::new(Mutex::new(Instant::now())),
        }
    }

    pub async fn call<F, T, E>(&self, f: F) -> Result<T, E>
    where
        F: FnOnce() -> Result<T, E>,
        E: From<&'static str>,
    {
        let current_state = *self.state.lock().await;

        match current_state {
            CircuitState::Open => {
                let elapsed = self.last_state_change.lock().await.elapsed();
                if elapsed >= Duration::from_secs(self.config.timeout_secs) {
                    *self.state.lock().await = CircuitState::HalfOpen;
                    self.failure_count.store(0, Ordering::SeqCst);
                    self.success_count.store(0, Ordering::SeqCst);
                    *self.last_state_change.lock().await = Instant::now();
                } else {
                    return Err("Circuit open".into());
                }
            }
            CircuitState::HalfOpen => {
                // Permite apenas uma requisição por vez (simplificado)
            }
            _ => {}
        }

        let result = f();

        match result {
            Ok(val) => {
                self.success_count.fetch_add(1, Ordering::SeqCst);
                let current_state = *self.state.lock().await;
                if current_state == CircuitState::HalfOpen {
                    let successes = self.success_count.load(Ordering::SeqCst);
                    if successes >= self.config.success_threshold {
                        *self.state.lock().await = CircuitState::Closed;
                        tracing::info!("✅ Circuit Breaker fechado (recuperado)");
                    }
                }
                if current_state == CircuitState::Closed {
                    self.failure_count.store(0, Ordering::SeqCst);
                }
                Ok(val)
            }
            Err(e) => {
                let failures = self.failure_count.fetch_add(1, Ordering::SeqCst) + 1;
                let current_state = *self.state.lock().await;
                if current_state == CircuitState::Closed && failures >= self.config.failure_threshold {
                    *self.state.lock().await = CircuitState::Open;
                    *self.last_state_change.lock().await = Instant::now();
                    tracing::warn!("🔌 Circuit Breaker aberto (threshold: {})", self.config.failure_threshold);
                } else if current_state == CircuitState::HalfOpen {
                    *self.state.lock().await = CircuitState::Open;
                    *self.last_state_change.lock().await = Instant::now();
                    tracing::warn!("🔌 Circuit Breaker reaberto (falha no HalfOpen)");
                }
                Err(e)
            }
        }
    }

    pub async fn get_state(&self) -> CircuitState {
        *self.state.lock().await
    }
}
