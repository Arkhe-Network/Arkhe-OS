use crate::tensor::Tensor;

pub struct Expert {
    pub gate_proj: Tensor,
    pub up_proj: Tensor,
    pub down_proj: Tensor,
    pub gate_bias: Tensor,
    pub up_bias: Tensor,
    pub down_bias: Tensor,
    pub clamp_limit: f32,
    pub hidden_size: usize,
    pub intermediate_size: usize,
}

impl Expert {
    pub fn new(hidden_size: usize, intermediate_size: usize) -> Self {
        Self {
            gate_proj: Tensor::randn((hidden_size, intermediate_size)),
            up_proj: Tensor::randn((hidden_size, intermediate_size)),
            down_proj: Tensor::randn((intermediate_size, hidden_size)),
            gate_bias: Tensor::zeros((1, intermediate_size)),
            up_bias: Tensor::zeros((1, intermediate_size)),
            down_bias: Tensor::zeros((1, hidden_size)),
            clamp_limit: 10.0,
            hidden_size,
            intermediate_size,
        }
    }

    pub fn forward(&self, x: &Tensor) -> Tensor {
        let gate = x.matmul(&self.gate_proj).add(&self.gate_bias);
        let up = x.matmul(&self.up_proj).add(&self.up_bias);
        let activated = self.swiglu_clamp(&gate, &up);
        activated.matmul(&self.down_proj).add(&self.down_bias)
    }

    fn swiglu_clamp(&self, gate: &Tensor, up: &Tensor) -> Tensor {
        let g = gate.clamp(-self.clamp_limit, self.clamp_limit);
        let u = up.clamp(-self.clamp_limit, self.clamp_limit);
        let sig_g = g.sigmoid();
        g.mul_elem(&sig_g).mul_elem(&u)
    }
}
