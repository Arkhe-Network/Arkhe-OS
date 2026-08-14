#![no_std]
#![warn(missing_docs, unsafe_op_in_unsafe_fn)]
#![cfg_attr(not(feature = "std"), no_std)]

extern crate alloc;

pub mod crypto_impl;
pub mod error;
pub mod fast_path;
pub mod key_hierarchy;
pub mod policy;
pub mod quantum_memory;
pub mod slow_path;
pub mod types;

pub use error::{AuthError, AuthResult};
pub use fast_path::{FastPathAuth, HeraldMessage};
pub use key_hierarchy::KeyHierarchy;
pub use policy::{PolicyContext, PolicyDecision, PolicyEngine, QuantumLinkPolicy};
pub use quantum_memory::QuantumMemoryController;
pub use slow_path::{SlowPathAuth, SlowPathMessage};
pub use types::{NodeId, StorageHandle};

#[cfg(feature = "std")]
pub use crypto_impl::{Aes256GcmSivAead, MlDsa65, XWingKem};

pub struct QuantumAuthStack<A, S, K, P>
where
    A: types::FastAead,
    S: types::PqSignature,
    K: types::PqKem,
    P: PolicyEngine,
{
    pub fast: FastPathAuth<A>,
    pub slow: SlowPathAuth<S, K>,
    pub policy: P,
    pub context: PolicyContext,
}

impl<A, S, K, P> QuantumAuthStack<A, S, K, P>
where
    A: types::FastAead,
    S: types::PqSignature,
    K: types::PqKem,
    P: PolicyEngine,
{
    pub fn new(
        fast: FastPathAuth<A>,
        slow: SlowPathAuth<S, K>,
        policy: P,
        context: PolicyContext,
    ) -> Self {
        Self {
            fast,
            slow,
            policy,
            context,
        }
    }

    pub fn receive_herald(&mut self, msg: &HeraldMessage) -> AuthResult<()> {
        match self.policy.evaluate_herald(msg, &self.context) {
            PolicyDecision::Allow => self.fast.verify_herald(msg),
            PolicyDecision::RateLimit { delay_ns } => {
                log::debug!("herald rate-limited: delay={}ns", delay_ns);
                Err(AuthError::PolicyViolation {
                    reason: alloc::format!("rate_limited:{}ns", delay_ns),
                })
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
        }
    }

    pub fn send_herald(&mut self, msg: &mut HeraldMessage) -> AuthResult<()> {
        match self.policy.evaluate_herald(msg, &self.context) {
            PolicyDecision::Allow => self.fast.seal_herald(msg),
            PolicyDecision::RateLimit { delay_ns } => {
                log::debug!("herald send rate-limited: delay={}ns", delay_ns);
                Err(AuthError::PolicyViolation {
                    reason: alloc::format!("rate_limited:{}ns", delay_ns),
                })
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
        }
    }

    pub fn rotate_keys(&mut self, new_counter: u64) -> AuthResult<SlowPathMessage> {
        let ts = platform::monotonic_ns();
        let cmd = self
            .slow
            .sign_rotation(new_counter, ts, &self.context.node_did);
        match self.policy.evaluate_slow(&cmd, &self.context) {
            PolicyDecision::Allow => {
                self.fast.key_hierarchy.rotate_session()?;
                self.context.last_rotation_ns = ts;
                Ok(cmd)
            }
            PolicyDecision::Reject { reason } => Err(AuthError::PolicyViolation { reason }),
            _ => Err(AuthError::PolicyViolation {
                reason: "rotation_rate_limited".into(),
            }),
        }
    }
}

pub mod platform {
    use core::sync::atomic::{AtomicU64, Ordering};

    static TIME_NS: AtomicU64 = AtomicU64::new(0);

    pub fn set_monotonic_ns(ns: u64) {
        TIME_NS.store(ns, Ordering::SeqCst);
    }

    pub fn tick_monotonic(delta_ns: u64) {
        TIME_NS.fetch_add(delta_ns, Ordering::Relaxed);
    }

    pub fn monotonic_ns() -> u64 {
        #[cfg(feature = "std")]
        {
            TIME_NS.load(Ordering::Relaxed) // fallback
        }
        #[cfg(not(feature = "std"))]
        {
            TIME_NS.load(Ordering::Relaxed)
        }
    }
}
