use crate::tensor::Tensor;

pub struct ManifoldConstrainedHyperConnections {
    pub expansion_rate: usize,
    pub phi_pre: Tensor,
    pub phi_post: Tensor,
    pub phi_res: Tensor,
    pub alpha_pre: f32,
    pub alpha_post: f32,
    pub alpha_res: f32,
    pub bias_pre: Tensor,
    pub bias_post: Tensor,
    pub bias_res: Tensor,
}

impl ManifoldConstrainedHyperConnections {
    pub fn new(hidden_size: usize, expansion_rate: usize) -> Self {
        let n = hidden_size;
        let c = expansion_rate;
        Self {
            expansion_rate: c,
            phi_pre: Tensor::randn((c * n, n)),
            phi_post: Tensor::randn((c * n, n)),
            phi_res: Tensor::randn((c * n, n * n)),
            alpha_pre: 0.5,
            alpha_post: 1.0,
            alpha_res: 1.0,
            bias_pre: Tensor::zeros((c * n, 1)),
            bias_post: Tensor::zeros((c * n, 1)),
            bias_res: Tensor::zeros((c * n, 1)),
        }
    }

    pub fn forward(&self, x: &Tensor, layer_fn: impl Fn(&Tensor) -> Tensor) -> Tensor {
        let x_flat = x.reshape((1, x.nrows() * x.ncols()));
        let x_norm = rms_norm(&x_flat);

        let h_pre_raw = x_norm
            .matmul(&Tensor::from(self.phi_pre.to_ndarray().t().to_owned()))
            .add(&Tensor::from(self.bias_pre.to_ndarray().t().to_owned()));
        let h_pre = h_pre_raw.sigmoid();

        let h_post_raw = x_norm
            .matmul(&Tensor::from(self.phi_post.to_ndarray().t().to_owned()))
            .add(&Tensor::from(self.bias_post.to_ndarray().t().to_owned()));
        let h_post = h_post_raw.sigmoid().scale(2.0);

        let h_res_raw = x_norm
            .matmul(&Tensor::from(self.phi_res.to_ndarray().t().to_owned()))
            .add(&Tensor::from(self.bias_res.to_ndarray().t().to_owned()));
        let h_res_flat = h_res_raw.reshape((
            self.expansion_rate,
            self.expansion_rate * x.ncols() * x.ncols(),
        ));
        let h_res = sinkhorn_knopp(&h_res_flat, 10);

        let x_vec = x.clone().reshape((1, x.nrows() * x.ncols()));
        let residual = h_res.matmul(&Tensor::from(x_vec.to_ndarray().t().to_owned()));

        let pre_x = h_pre.matmul(&Tensor::from(x_vec.to_ndarray().t().to_owned()));
        let transformed = layer_fn(&pre_x);
        let transformed = h_post.matmul(&Tensor::from(transformed.to_ndarray().t().to_owned()));

        residual.add(&transformed).reshape((1, x.ncols()))
    }
}

fn rms_norm(x: &Tensor) -> Tensor {
    let mean_sq = x.mapv(|v| v * v).mean_axis(1);
    let scale = mean_sq.sqrt().mapv(|v| 1.0 / (v + 1e-6));
    let mut x_scaled = x.clone();
    for i in 0..x.nrows() {
        let s = scale.to_ndarray()[[i, 0]];
        for j in 0..x.ncols() {
            x_scaled.to_ndarray_mut()[[i, j]] *= s;
        }
    }
    x_scaled
}

fn sinkhorn_knopp(m: &Tensor, iterations: usize) -> Tensor {
    let mut w = m.clone();
    let (rows, cols) = w.shape();

    for _ in 0..iterations {
        for i in 0..rows {
            let sum = w.row(i).sum();
            if sum > 0.0 {
                for j in 0..cols {
                    w.to_ndarray_mut()[[i, j]] /= sum;
                }
            }
        }
        for j in 0..cols {
            let sum = w.col(j).sum();
            if sum > 0.0 {
                for i in 0..rows {
                    w.to_ndarray_mut()[[i, j]] /= sum;
                }
            }
        }
    }
    w
}
