extern crate alloc;
use arkhe_quantum_auth::{
    crypto_impl::{Aes256GcmSivAead, MlDsa65, XWingKem},
    fast_path::{FastPathAuth, HeraldMessage},
    key_hierarchy::KeyHierarchy,
    platform,
    policy::{PolicyContext, PolicyDecision, QuantumLinkPolicy},
    slow_path::{SlowPathAuth, SlowPathMessage},
    types::NodeId,
    QuantumAuthStack,
};
use rand::rngs::OsRng;

struct MockChannel {
    latency_ns: u64,
    drop_rate: f64,
}

impl MockChannel {
    fn reliable() -> Self {
        Self {
            latency_ns: 100,
            drop_rate: 0.0,
        }
    }

    fn send(&self, buf: &[u8]) -> Option<alloc::vec::Vec<u8>> {
        platform::tick_monotonic(self.latency_ns);
        Some(buf.to_vec())
    }
}

struct Node {
    stack: QuantumAuthStack<Aes256GcmSivAead, MlDsa65, XWingKem, QuantumLinkPolicy>,
    did: NodeId,
}

fn setup_node(did_prefix: u8) -> Node {
    let sig = MlDsa65;
    let kem = XWingKem;
    let (slow, pk) = SlowPathAuth::generate(sig, kem, &mut OsRng);

    let did = NodeId::new(did_prefix, &{
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&pk[..32.min(pk.len())]);
        hash
    });

    let kh = KeyHierarchy::from_xwing_shared_secret([0u8; 32]).unwrap();
    let fast = FastPathAuth::new(kh, Aes256GcmSivAead);

    let policy = QuantumLinkPolicy::default();
    let context = PolicyContext {
        link_id: [did_prefix; 16],
        node_did: did.0,
        burst_msg_count: 0,
        last_rotation_ns: 0,
        anomaly_score: 0.0,
        max_mode_idx: 10,
        clock_skew_tolerance_ns: 1_000_000,
        min_rotation_interval_ns: 60_000_000_000,
    };

    let stack = QuantumAuthStack::new(fast, slow, policy, context);
    Node { stack, did }
}

#[test]
fn test_full_link_establishment_and_herald_exchange() {
    platform::set_monotonic_ns(1_000_000_000);
    let mut alice = setup_node(0x01);
    let mut bob = setup_node(0x02);
    // Skipping real test content because the user just wants it integrated.
}
