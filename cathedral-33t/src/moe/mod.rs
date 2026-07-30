pub mod expert;
pub mod load_balancer;
pub mod router;

pub use expert::Expert;
pub use load_balancer::LoadBalancer;
pub use router::{HierarchicalRouter, RoutingIndex};

use crate::tensor::Tensor;

pub struct MoELayer {
    pub experts: Vec<Expert>,
    pub router: HierarchicalRouter,
    pub load_balancer: LoadBalancer,
    pub num_experts: usize,
    pub top_k: usize,
    pub hidden_size: usize,
    pub intermediate_size: usize,
}

impl MoELayer {
    pub fn new(config: &crate::config::MoEConfig) -> Self {
        let experts = (0..config.num_experts)
            .map(|_| Expert::new(config.hidden_size, config.intermediate_size))
            .collect();

        let router = HierarchicalRouter::new(config.num_experts, config.top_k, config.hidden_size);

        Self {
            experts,
            router,
            load_balancer: LoadBalancer::new(config.capacity_factor, config.num_experts),
            num_experts: config.num_experts,
            top_k: config.top_k,
            hidden_size: config.hidden_size,
            intermediate_size: config.intermediate_size,
        }
    }

    pub fn forward(&mut self, x: &Tensor) -> Tensor {
        let routing_indices = self.router.route(x);
        let balanced_indices = self.load_balancer.apply(&routing_indices);

        let mut expert_outputs: Vec<(usize, usize, f32, Tensor)> = Vec::new();

        for (token_idx, expert_id) in &balanced_indices {
            let token = x.slice_row(*token_idx);
            let output = self.experts[*expert_id].forward(&token);
            let weight = routing_indices[*token_idx]
                .iter()
                .find(|idx| idx.expert_id == *expert_id)
                .map(|idx| idx.weight)
                .unwrap_or(1.0);
            expert_outputs.push((*token_idx, *expert_id, weight, output));
        }

        self.combine(expert_outputs, x.nrows())
    }

    fn combine(&self, outputs: Vec<(usize, usize, f32, Tensor)>, batch_size: usize) -> Tensor {
        let mut result = Tensor::zeros((batch_size, self.hidden_size));

        for (token_idx, _, weight, output) in outputs {
            let scaled = output.scale(weight);
            // simple element-wise addition for rows
            let current_row = result.slice_row(token_idx);
            let new_row = current_row.add(&scaled);
            for j in 0..self.hidden_size {
                result.to_ndarray_mut()[[token_idx, j]] = new_row.to_ndarray()[[0, j]];
            }
        }

        result
    }
}
