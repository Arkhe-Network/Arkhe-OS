use crate::reactive_log::ReactiveLog;
use crate::governance::{GovernanceAction, GovernanceEntry, GovernanceError};
use std::sync::Arc;
use std::time::Duration;
use tracing::{error, info};

#[derive(Debug, Clone)]
pub struct WatchdogConfig {
    pub check_interval_secs: u64,
    pub consecutive_failures_threshold: u32,
    pub governance_key_id: String,
}

pub struct GovernanceWatchdog {
    log: Arc<tokio::sync::RwLock<ReactiveLog>>,
    config: WatchdogConfig,
    consecutive_attestation_failures: u32,
}

#[derive(Default)]
struct MetricsSnapshot {
    attestation_trusted: f64,
    ued_teacher_failure_rate: f64,
}

impl GovernanceWatchdog {
    pub fn new(log: Arc<tokio::sync::RwLock<ReactiveLog>>, config: WatchdogConfig) -> Self {
        Self {
            log,
            config,
            consecutive_attestation_failures: 0,
        }
    }

    pub async fn run(&mut self) {
        let mut interval = tokio::time::interval(Duration::from_secs(self.config.check_interval_secs));
        loop {
            interval.tick().await;
            self.check_and_act().await;
        }
    }

    async fn check_and_act(&mut self) {
        let metrics = self.collect_metrics().await;

        if metrics.attestation_trusted == 0.0 {
            self.consecutive_attestation_failures += 1;
        } else {
            self.consecutive_attestation_failures = 0;
        }

        if self.consecutive_attestation_failures >= self.config.consecutive_failures_threshold {
            let action = GovernanceAction::EmergencyFreeze {
                reason: format!(
                    "Attestation failure for {} consecutive checks",
                    self.consecutive_attestation_failures
                ),
                duration_seconds: 300,
            };
            if let Err(e) = self.propose_governance(action).await {
                error!("Failed to propose governance action: {}", e);
            }
            self.consecutive_attestation_failures = 0;
        }

        if metrics.ued_teacher_failure_rate > 0.5 {
            let action = GovernanceAction::AdjustTeacherReward {
                teacher_id: "default-teacher".to_string(),
                environment_hash: "".to_string(),
                reward_delta: -0.2,
                reason: "High failure rate detected".to_string(),
            };
            if let Err(e) = self.propose_governance(action).await {
                error!("Failed to propose teacher reward adjustment: {}", e);
            }
        }
    }

    async fn collect_metrics(&self) -> MetricsSnapshot {
        MetricsSnapshot {
            attestation_trusted: 1.0,
            ued_teacher_failure_rate: 0.0,
        }
    }

    async fn propose_governance(&self, action: GovernanceAction) -> Result<(), GovernanceError> {
        let signature = vec![];
        let verifying_key = vec![];

        let entry = GovernanceEntry {
            action,
            issued_by: "watchdog".to_string(),
            timestamp: chrono::Utc::now().timestamp(),
            signature,
            verifying_key,
        };

        info!("Watchdog proposing action: {:?}", entry);
        let mut log = self.log.write().await;
        log.apply_governance_entry(entry).await?;
        Ok(())
    }
}
