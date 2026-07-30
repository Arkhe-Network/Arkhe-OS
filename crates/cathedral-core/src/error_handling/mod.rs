pub mod retry;
pub mod circuit_breaker;

#[cfg(test)]
mod tests {
    use super::retry::{RetryConfig, RetryContext};
    use super::circuit_breaker::{CircuitBreaker, CircuitBreakerConfig, CircuitState};
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Arc;

    #[tokio::test]
    async fn test_retry_success() {
        let config = RetryConfig {
            max_retries: 3,
            base_delay_ms: 10,
            max_delay_ms: 50,
            backoff_factor: 2.0,
        };
        let mut ctx = RetryContext::new(config);

        let counter = Arc::new(AtomicUsize::new(0));
        let c_clone = counter.clone();

        let result = ctx.retry(move || {
            let attempt = c_clone.fetch_add(1, Ordering::SeqCst);
            if attempt < 2 {
                Err("Failed")
            } else {
                Ok("Success")
            }
        }).await;

        assert_eq!(result, Ok("Success"));
        assert_eq!(counter.load(Ordering::SeqCst), 3);
    }

    #[tokio::test]
    async fn test_circuit_breaker() {
        let config = CircuitBreakerConfig {
            failure_threshold: 2,
            success_threshold: 1,
            timeout_secs: 1,
        };
        let cb = CircuitBreaker::new(config);

        // Success
        let res = cb.call(|| Ok::<&str, &str>("ok")).await;
        assert_eq!(res, Ok("ok"));
        assert_eq!(cb.get_state().await, CircuitState::Closed);

        // Failures to open
        let _ = cb.call(|| Err::<&str, &str>("err")).await;
        let _ = cb.call(|| Err::<&str, &str>("err")).await;
        assert_eq!(cb.get_state().await, CircuitState::Open);

        // Fast fail when open
        let res2 = cb.call(|| Ok::<&str, &str>("ok")).await;
        assert_eq!(res2, Err("Circuit open"));
    }
}
