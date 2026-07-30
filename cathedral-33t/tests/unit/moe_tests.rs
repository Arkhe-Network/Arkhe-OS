
use crate::config::MoEConfig;
use crate::moe::{MoELayer, HierarchicalRouter};
use crate::tensor::Tensor;

#[test]
fn test_router_route() {
    let router = HierarchicalRouter::new(4096, 8, 8192);
    let x = Tensor::randn((2, 8192));
    let routing = router.route(&x);
    assert_eq!(routing.len(), 2);
    for entry in routing {
        assert_eq!(entry.len(), 8);
    }
}

#[test]
fn test_moe_forward() {
    let config = MoEConfig {
        num_experts: 64,
        top_k: 4,
        hidden_size: 128,
        intermediate_size: 512,
        capacity_factor: 1.25,
        load_balancing_loss_coef: 0.01,
    };
    let mut moe = MoELayer::new(&config);
    let x = Tensor::randn((2, 128));
    let output = moe.forward(&x);
    assert_eq!(output.shape(), (2, 128));
}
