use ndarray::Array1;
use std::sync::Arc;
use super::causal_inner_product::CovarianceMatrix;

pub struct SubspaceOperations {
    cov: Arc<CovarianceMatrix>,
}

impl SubspaceOperations {
    pub fn new(cov: Arc<CovarianceMatrix>) -> Self {
        Self { cov }
    }

    pub fn project_to_known_subspace(&self, v: &Array1<f32>) -> Array1<f32> {
        v.clone()
    }

    pub fn causal_weight(&self, v: &Array1<f32>) -> f32 {
        1.0
    }
}
