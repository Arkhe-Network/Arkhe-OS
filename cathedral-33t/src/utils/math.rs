use crate::tensor::Tensor;

pub fn clip_gradients(grads: &mut [Tensor], max_norm: f32) {
    let mut total_norm = 0.0f32;
    for grad in grads.iter() {
        total_norm += grad.mapv(|v| v * v).sum();
    }
    total_norm = total_norm.sqrt();

    if total_norm > max_norm {
        let scale = max_norm / total_norm;
        for grad in grads.iter_mut() {
            *grad = grad.scale(scale);
        }
    }
}
