use crate::tensor::Tensor;

pub struct MONALiteOptimizer {
    clip_norm: Option<f32>,
    muon: MuonOptimizer,
    acceleration_buffers: Vec<Tensor>,
    beta_a: f32,
    alpha: f32,
    streaming: bool,
    prev_grads: Option<Vec<Tensor>>,
}

impl MONALiteOptimizer {
    pub fn new(
        param_shapes: &[(usize, usize)],
        lr: f32,
        beta_a: f32,
        alpha: f32,
        clip_norm: Option<f32>,
    ) -> Self {
        let buffers = param_shapes
            .iter()
            .map(|&shape| Tensor::zeros(shape))
            .collect();

        Self {
            muon: MuonOptimizer::new(lr),
            acceleration_buffers: buffers,
            beta_a,
            alpha,
            streaming: true,
            prev_grads: None,
            clip_norm,
        }
    }

    pub fn step(&mut self, grads: &mut [Tensor]) {
        if let Some(max_norm) = self.clip_norm {
            crate::utils::math::clip_gradients(grads, max_norm);
        }
        let lr = self.muon.lr();

        for (i, grad) in grads.iter().enumerate() {
            let diff = if self.streaming {
                if let Some(prev) = &self.prev_grads {
                    grad.sub(&prev[i])
                } else {
                    grad.clone()
                }
            } else {
                grad.clone()
            };

            self.acceleration_buffers[i] = self.acceleration_buffers[i]
                .scale(self.beta_a)
                .add(&diff.scale(1.0 - self.beta_a));

            let accelerated = grad.add(&self.acceleration_buffers[i].scale(self.alpha));

            self.muon.step_single(&accelerated, lr, i);
        }

        self.prev_grads = Some(grads.to_vec());
    }
}

struct MuonOptimizer {
    lr: f32,
}

impl MuonOptimizer {
    pub fn new(lr: f32) -> Self {
        Self { lr }
    }

    pub fn lr(&self) -> f32 {
        self.lr
    }

    pub fn step_single(&mut self, grad: &Tensor, lr: f32, _idx: usize) {
        let _ = grad.scale(lr);
    }
}
