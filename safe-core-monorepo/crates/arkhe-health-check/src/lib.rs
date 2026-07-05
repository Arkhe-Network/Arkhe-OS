// crates/arkhe-health-check/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Health checks para componentes do Arkhe OS.
//!
//! Fornece:
//! - **Liveness**: o componente está vivo? (processo rodando)
//! - **Readiness**: o componente pode aceitar tráfego? (dependências OK)
//! - **Startup**: o componente terminou de inicializar?

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum HealthError {
    #[error("check timed out after {duration:?}")]
    Timeout { duration: Duration },

    #[error("dependency '{name}' is unhealthy: {reason}")]
    DependencyUnhealthy { name: String, reason: String },
}

pub type HealthResult<T> = Result<T, HealthError>;

/// Status de saúde.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    /// Saudável.
    Healthy,
    /// Degradado — funcionando mas com problemas.
    Degraded,
    /// Não saudável — não pode aceitar tráfego.
    Unhealthy,
    /// Desconhecido — check não foi executado ainda.
    Unknown,
}

impl std::fmt::Display for HealthStatus {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HealthStatus::Healthy => write!(f, "HEALTHY"),
            HealthStatus::Degraded => write!(f, "DEGRADED"),
            HealthStatus::Unhealthy => write!(f, "UNHEALTHY"),
            HealthStatus::Unknown => write!(f, "UNKNOWN"),
        }
    }
}

/// Resultado de um health check individual.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckResult {
    /// Nome do componente.
    pub component: String,
    /// Status.
    pub status: HealthStatus,
    /// Mensagem legível.
    pub message: String,
    /// Duração do check.
    pub duration_ms: u64,
    /// Timestamp.
    pub checked_at: DateTime<Utc>,
    /// Detalhes extras.
    pub details: HashMap<String, serde_json::Value>,
}

/// Resultado agregado de saúde do sistema.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthReport {
    /// Status geral (pior dos componentes).
    pub status: HealthStatus,
    /// Versão do Arkhe.
    pub version: String,
    /// Uptime em segundos (se disponível).
    pub uptime_secs: Option<u64>,
    /// Resultados por componente.
    pub checks: Vec<CheckResult>,
    /// Timestamp do relatório.
    pub generated_at: DateTime<Utc>,
}

/// Trait para componentes que podem reportar saúde.
pub trait HealthCheckable: Send + Sync {
    /// Nome do componente.
    fn name(&self) -> &str;

    /// Executa o check de liveness (está vivo?).
    fn check_liveness(&self) -> CheckResult;

    /// Executa o check de readiness (pode aceitar tráfego?).
    fn check_readiness(&self) -> CheckResult;

    /// Executa o check de startup (terminou de iniciar?).
    fn check_startup(&self) -> CheckResult {
        // Default: startup é sempre true após primeiro liveness check
        let liveness = self.check_liveness();
        CheckResult {
            component: format!("{}:startup", self.name()),
            status: if liveness.status == HealthStatus::Healthy { HealthStatus::Healthy } else { HealthStatus::Unhealthy },
            message: liveness.message,
            duration_ms: liveness.duration_ms,
            checked_at: liveness.checked_at,
            details: HashMap::new(),
        }
    }
}

/// Health checker que agrega múltiplos componentes.
pub struct HealthChecker {
    components: Vec<Box<dyn HealthCheckable>>,
    started_at: Instant,
    version: String,
}

impl HealthChecker {
    pub fn new(version: &str) -> Self {
        Self {
            components: Vec::new(),
            started_at: Instant::now(),
            version: version.into(),
        }
    }

    /// Registra um componente.
    pub fn register(&mut self, component: Box<dyn HealthCheckable>) {
        self.components.push(component);
    }

    /// Gera relatório de liveness.
    pub fn liveness(&self) -> HealthReport {
        let checks: Vec<CheckResult> = self.components.iter().map(|c| c.check_liveness()).collect();
        self.aggregate(checks)
    }

    /// Gera relatório de readiness.
    pub fn readiness(&self) -> HealthReport {
        let checks: Vec<CheckResult> = self.components.iter().map(|c| c.check_readiness()).collect();
        self.aggregate(checks)
    }

    /// Gera relatório de startup.
    pub fn startup(&self) -> HealthReport {
        let checks: Vec<CheckResult> = self.components.iter().map(|c| c.check_startup()).collect();
        self.aggregate(checks)
    }

    fn aggregate(&self, checks: Vec<CheckResult>) -> HealthReport {
        let overall = checks.iter().map(|c| c.status).max().unwrap_or(HealthStatus::Unknown);
        // Unknown < Degraded < Unhealthy < Healthy — mas para aggregate,
        // qualquer Unhealthy torna tudo Unhealthy
        let status = if checks.iter().any(|c| c.status == HealthStatus::Unhealthy) {
            HealthStatus::Unhealthy
        } else if checks.iter().any(|c| c.status == HealthStatus::Degraded) {
            HealthStatus::Degraded
        } else if checks.is_empty() {
            HealthStatus::Unknown
        } else {
            HealthStatus::Healthy
        };

        HealthReport {
            status,
            version: self.version.clone(),
            uptime_secs: Some(self.started_at.elapsed().as_secs()),
            checks,
            generated_at: Utc::now(),
        }
    }
}

/// Implementação simples de health check para qualquer closure.
pub struct FnHealthCheck {
    name: String,
    liveness_fn: Box<dyn Fn() -> CheckResult + Send + Sync>,
    readiness_fn: Box<dyn Fn() -> CheckResult + Send + Sync>,
}

impl FnHealthCheck {
    pub fn new<F1, F2>(name: &str, liveness: F1, readiness: F2) -> Self
    where
        F1: Fn() -> CheckResult + Send + Sync + 'static,
        F2: Fn() -> CheckResult + Send + Sync + 'static,
    {
        Self {
            name: name.into(),
            liveness_fn: Box::new(liveness),
            readiness_fn: Box::new(readiness),
        }
    }
}

impl HealthCheckable for FnHealthCheck {
    fn name(&self) -> &str { &self.name }
    fn check_liveness(&self) -> CheckResult { (self.liveness_fn)() }
    fn check_readiness(&self) -> CheckResult { (self.readiness_fn)() }
}

/// Helper para criar CheckResult rápido.
pub fn healthy(component: &str, message: &str) -> CheckResult {
    CheckResult {
        component: component.into(),
        status: HealthStatus::Healthy,
        message: message.into(),
        duration_ms: 0,
        checked_at: Utc::now(),
        details: HashMap::new(),
    }
}

pub fn unhealthy(component: &str, message: &str) -> CheckResult {
    CheckResult {
        component: component.into(),
        status: HealthStatus::Unhealthy,
        message: message.into(),
        duration_ms: 0,
        checked_at: Utc::now(),
        details: HashMap::new(),
    }
}

pub fn degraded(component: &str, message: &str) -> CheckResult {
    CheckResult {
        component: component.into(),
        status: HealthStatus::Degraded,
        message: message.into(),
        duration_ms: 0,
        checked_at: Utc::now(),
        details: HashMap::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct AlwaysHealthy;
    impl HealthCheckable for AlwaysHealthy {
        fn name(&self) -> &str { "always_healthy" }
        fn check_liveness(&self) -> CheckResult { healthy("always_healthy", "ok") }
        fn check_readiness(&self) -> CheckResult { healthy("always_healthy", "ok") }
    }

    struct AlwaysUnhealthy;
    impl HealthCheckable for AlwaysUnhealthy {
        fn name(&self) -> &str { "always_unhealthy" }
        fn check_liveness(&self) -> CheckResult { unhealthy("always_unhealthy", "down") }
        fn check_readiness(&self) -> CheckResult { unhealthy("always_unhealthy", "down") }
    }

    struct SometimesDegraded;
    impl HealthCheckable for SometimesDegraded {
        fn name(&self) -> &str { "sometimes_degraded" }
        fn check_liveness(&self) -> CheckResult { healthy("sometimes_degraded", "alive") }
        fn check_readiness(&self) -> CheckResult { degraded("sometimes_degraded", "slow") }
    }

    #[test]
    fn all_healthy_report() {
        let mut checker = HealthChecker::new("0.1.0");
        checker.register(Box::new(AlwaysHealthy));
        let report = checker.liveness();
        assert_eq!(report.status, HealthStatus::Healthy);
        assert_eq!(report.checks.len(), 1);
    }

    #[test]
    fn one_unhealthy_makes_all_unhealthy() {
        let mut checker = HealthChecker::new("0.1.0");
        checker.register(Box::new(AlwaysHealthy));
        checker.register(Box::new(AlwaysUnhealthy));
        let report = checker.readiness();
        assert_eq!(report.status, HealthStatus::Unhealthy);
    }

    #[test]
    fn degraded_without_unhealthy() {
        let mut checker = HealthChecker::new("0.1.0");
        checker.register(Box::new(SometimesDegraded));
        let report = checker.readiness();
        assert_eq!(report.status, HealthStatus::Degraded);
    }

    #[test]
    fn empty_checker_is_unknown() {
        let checker = HealthChecker::new("0.1.0");
        let report = checker.liveness();
        assert_eq!(report.status, HealthStatus::Unknown);
        assert!(report.uptime_secs.is_some());
    }

    #[test]
    fn report_has_version_and_uptime() {
        let mut checker = HealthChecker::new("7.0.0");
        checker.register(Box::new(AlwaysHealthy));
        let report = checker.liveness();
        assert_eq!(report.version, "7.0.0");
        assert!(report.uptime_secs.unwrap() < 1);
    }

    #[test]
    fn fn_health_check() {
        let check = FnHealthCheck::new(
            "fn_check",
            || healthy("fn_check:liveness", "ok"),
            || healthy("fn_check:readiness", "ok"),
        );

        let mut checker = HealthChecker::new("0.1.0");
        checker.register(Box::new(check));
        let report = checker.liveness();
        assert_eq!(report.status, HealthStatus::Healthy);
    }

    #[test]
    fn status_display() {
        assert_eq!(HealthStatus::Healthy.to_string(), "HEALTHY");
        assert_eq!(HealthStatus::Unhealthy.to_string(), "UNHEALTHY");
        assert_eq!(HealthStatus::Degraded.to_string(), "DEGRADED");
        assert_eq!(HealthStatus::Unknown.to_string(), "UNKNOWN");
    }
}
