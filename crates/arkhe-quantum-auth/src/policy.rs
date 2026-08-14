use crate::fast_path::HeraldMessage;
use crate::slow_path::SlowPathMessage;
use alloc::format;
use alloc::string::String;

#[derive(Debug, Clone, PartialEq)]
pub enum PolicyDecision {
    Allow,
    RateLimit { delay_ns: u64 },
    Reject { reason: String },
}

#[derive(Debug, Clone)]
pub struct PolicyContext {
    pub link_id: [u8; 16],
    pub node_did: [u8; 33],
    pub burst_msg_count: u64,
    pub last_rotation_ns: u64,
    pub anomaly_score: f64,
    pub max_mode_idx: u8,
    pub clock_skew_tolerance_ns: u64,
    pub min_rotation_interval_ns: u64,
}

impl Default for PolicyContext {
    fn default() -> Self {
        Self {
            link_id: [0u8; 16],
            node_did: [0u8; 33],
            burst_msg_count: 0,
            last_rotation_ns: 0,
            anomaly_score: 0.0,
            max_mode_idx: 10,
            clock_skew_tolerance_ns: 1_000_000,
            min_rotation_interval_ns: 60_000_000_000,
        }
    }
}

pub trait PolicyEngine {
    fn evaluate_herald(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> PolicyDecision;
    fn evaluate_slow(&self, msg: &SlowPathMessage, ctx: &PolicyContext) -> PolicyDecision;
    fn update_context(&self, ctx: &mut PolicyContext, _msg: &HeraldMessage) {
        ctx.burst_msg_count += 1;
    }
}

pub struct QuantumLinkPolicy {
    pub max_msgs_per_burst: u64,
    pub max_burst_rate: f64,
    pub anomaly_threshold: f64,
}

impl Default for QuantumLinkPolicy {
    fn default() -> Self {
        Self {
            max_msgs_per_burst: 100_000,
            max_burst_rate: 1e6,
            anomaly_threshold: 0.95,
        }
    }
}

impl PolicyEngine for QuantumLinkPolicy {
    fn evaluate_herald(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> PolicyDecision {
        if msg.mode_idx > ctx.max_mode_idx {
            log::warn!(
                "policy reject: mode_idx={} > max={}",
                msg.mode_idx,
                ctx.max_mode_idx
            );
            return PolicyDecision::Reject {
                reason: format!("invalid_mode_idx:{}", msg.mode_idx),
            };
        }

        let now = crate::platform::monotonic_ns();
        if msg.timestamp_ns > now.saturating_add(ctx.clock_skew_tolerance_ns) {
            log::warn!(
                "policy reject: future timestamp {} > now {} + tolerance",
                msg.timestamp_ns,
                now
            );
            return PolicyDecision::Reject {
                reason: "future_timestamp".into(),
            };
        }

        if ctx.burst_msg_count > self.max_msgs_per_burst {
            log::debug!("policy rate-limit: burst_msg_count={}", ctx.burst_msg_count);
            return PolicyDecision::RateLimit { delay_ns: 1000 };
        }

        if ctx.anomaly_score > self.anomaly_threshold {
            log::warn!("policy reject: anomaly_score={}", ctx.anomaly_score);
            return PolicyDecision::Reject {
                reason: format!("anomaly_detected:{:.4}", ctx.anomaly_score),
            };
        }

        PolicyDecision::Allow
    }

    fn evaluate_slow(&self, _msg: &SlowPathMessage, ctx: &PolicyContext) -> PolicyDecision {
        let now = crate::platform::monotonic_ns();
        let elapsed = now.saturating_sub(ctx.last_rotation_ns);
        if elapsed < ctx.min_rotation_interval_ns {
            let remaining = ctx.min_rotation_interval_ns - elapsed;
            log::debug!("slow path rate-limit: {}ns remaining", remaining);
            return PolicyDecision::RateLimit {
                delay_ns: remaining,
            };
        }
        PolicyDecision::Allow
    }
}

#[cfg(feature = "arkhe-pea")]
pub trait ArkhePeaBridge {
    fn to_pea_request(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> arkhe_pea::PolicyRequest;
    fn from_pea_decision(&self, decision: arkhe_pea::PolicyDecision) -> PolicyDecision;
}

#[cfg(feature = "arkhe-pea")]
pub struct PeaPolicyEngine<B: ArkhePeaBridge> {
    bridge: B,
    inner: QuantumLinkPolicy,
}

#[cfg(feature = "arkhe-pea")]
impl<B: ArkhePeaBridge> PolicyEngine for PeaPolicyEngine<B> {
    fn evaluate_herald(&self, msg: &HeraldMessage, ctx: &PolicyContext) -> PolicyDecision {
        let local = self.inner.evaluate_herald(msg, ctx);
        match local {
            PolicyDecision::Allow => {
                let _req = self.bridge.to_pea_request(msg, ctx);
                local
            }
            _ => local,
        }
    }

    fn evaluate_slow(&self, msg: &SlowPathMessage, ctx: &PolicyContext) -> PolicyDecision {
        self.inner.evaluate_slow(msg, ctx)
    }
}
