use std::time::Duration;
use tokio::time::sleep;

#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_retries: usize,
    pub base_delay_ms: u64,
    pub max_delay_ms: u64,
    pub backoff_factor: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            base_delay_ms: 100,
            max_delay_ms: 5000,
            backoff_factor: 2.0,
        }
    }
}

pub struct RetryContext {
    config: RetryConfig,
    attempt: usize,
}

impl RetryContext {
    pub fn new(config: RetryConfig) -> Self {
        Self { config, attempt: 0 }
    }

    pub async fn retry<F, T, E>(&mut self, mut f: F) -> Result<T, E>
    where
        F: FnMut() -> Result<T, E>,
        E: std::fmt::Display,
    {
        loop {
            self.attempt += 1;
            match f() {
                Ok(result) => return Ok(result),
                Err(e) => {
                    if self.attempt >= self.config.max_retries {
                        return Err(e);
                    }
                    let delay = self.calculate_delay();
                    tracing::warn!(
                        "⏳ Tentativa {} falhou: {}. Retentando em {}ms...",
                        self.attempt, e, delay.as_millis()
                    );
                    sleep(delay).await;
                }
            }
        }
    }

    pub async fn retry_async<F, T, E>(&mut self, mut f: F) -> Result<T, E>
    where
        F: FnMut() -> futures::future::BoxFuture<'static, Result<T, E>>,
        E: std::fmt::Display + Send + Sync,
    {
        loop {
            self.attempt += 1;
            match f().await {
                Ok(result) => return Ok(result),
                Err(e) => {
                    if self.attempt >= self.config.max_retries {
                        return Err(e);
                    }
                    let delay = self.calculate_delay();
                    tracing::warn!(
                        "⏳ Tentativa {} falhou: {}. Retentando em {}ms...",
                        self.attempt, e, delay.as_millis()
                    );
                    sleep(delay).await;
                }
            }
        }
    }

    fn calculate_delay(&self) -> Duration {
        let delay = (self.config.base_delay_ms as f64 * self.config.backoff_factor.powi(self.attempt as i32 - 1))
            .min(self.config.max_delay_ms as f64);
        Duration::from_millis(delay as u64)
    }
}

#[macro_export]
macro_rules! with_retry {
    ($config:expr, $block:expr) => {{
        let mut ctx = $crate::error_handling::retry::RetryContext::new($config);
        ctx.retry_async(|| Box::pin(async { $block })).await
    }};
}
