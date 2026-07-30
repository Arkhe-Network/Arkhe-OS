use ndarray::Array2;
use ndarray_rand::RandomExt;
use rand::distributions::Standard;
use rand::rngs::StdRng;
use rand::SeedableRng;
use serde::{Deserialize, Serialize};
use std::ops::{Add, Mul, Sub};

pub type Shape = Vec<usize>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Tensor {
    pub(crate) data: Array2<f32>,
}

impl Tensor {
    pub fn zeros(shape: (usize, usize)) -> Self {
        Self {
            data: Array2::zeros(shape),
        }
    }

    pub fn randn(shape: (usize, usize)) -> Self {
        let mut rng = StdRng::seed_from_u64(42);
        Self {
            data: Array2::random_using(shape, Standard, &mut rng),
        }
    }

    pub fn full(shape: (usize, usize), value: f32) -> Self {
        Self {
            data: Array2::from_elem(shape, value),
        }
    }

    pub fn shape(&self) -> (usize, usize) {
        let dims = self.data.shape();
        (dims[0], dims[1])
    }

    pub fn nrows(&self) -> usize {
        self.data.shape()[0]
    }
    pub fn ncols(&self) -> usize {
        self.data.shape()[1]
    }

    pub fn to_vec(&self) -> Vec<f32> {
        self.data.iter().copied().collect()
    }

    pub fn row(&self, idx: usize) -> Tensor {
        Tensor {
            data: self.data.row(idx).to_owned().insert_axis(ndarray::Axis(0)),
        }
    }

    pub fn col(&self, idx: usize) -> Tensor {
        Tensor {
            data: self
                .data
                .column(idx)
                .to_owned()
                .insert_axis(ndarray::Axis(1)),
        }
    }

    pub fn slice_row(&self, idx: usize) -> Tensor {
        Tensor {
            data: self
                .data
                .slice(ndarray::s![idx, ..])
                .to_owned()
                .insert_axis(ndarray::Axis(0)),
        }
    }

    pub fn add(&self, other: &Tensor) -> Tensor {
        Tensor {
            data: &self.data + &other.data,
        }
    }

    pub fn sub(&self, other: &Tensor) -> Tensor {
        Tensor {
            data: &self.data - &other.data,
        }
    }

    pub fn mul_elem(&self, other: &Tensor) -> Tensor {
        Tensor {
            data: &self.data * &other.data,
        }
    }

    pub fn scale(&self, scalar: f32) -> Tensor {
        Tensor {
            data: &self.data * scalar,
        }
    }

    pub fn matmul(&self, other: &Tensor) -> Tensor {
        Tensor {
            data: self.data.dot(&other.data),
        }
    }

    pub fn mapv(&self, f: impl Fn(f32) -> f32) -> Tensor {
        Tensor {
            data: self.data.mapv(f),
        }
    }

    pub fn clamp(&self, min: f32, max: f32) -> Tensor {
        self.mapv(|v| v.clamp(min, max))
    }

    pub fn sum_axis(&self, axis: usize) -> Tensor {
        let sum = if axis == 0 {
            self.data
                .sum_axis(ndarray::Axis(0))
                .insert_axis(ndarray::Axis(0))
        } else if axis == 1 {
            self.data
                .sum_axis(ndarray::Axis(1))
                .insert_axis(ndarray::Axis(1))
        } else {
            panic!("Axis must be 0 or 1");
        };
        Tensor { data: sum }
    }

    pub fn mean_axis(&self, axis: usize) -> Tensor {
        let len = if axis == 0 {
            self.nrows()
        } else {
            self.ncols()
        } as f32;
        self.sum_axis(axis).scale(1.0 / len)
    }

    pub fn reshape(&self, new_shape: (usize, usize)) -> Tensor {
        let new_len = new_shape.0 * new_shape.1;
        let old_len = self.data.len();
        assert_eq!(new_len, old_len, "Total elements must match");
        Tensor {
            data: self.data.clone().into_shape(new_shape).unwrap(),
        }
    }

    pub fn sigmoid(&self) -> Tensor {
        self.mapv(|v| 1.0 / (1.0 + (-v).exp()))
    }

    pub fn exp(&self) -> Tensor {
        self.mapv(|v| v.exp())
    }
    pub fn sqrt(&self) -> Tensor {
        self.mapv(|v| v.sqrt())
    }
    pub fn abs(&self) -> Tensor {
        self.mapv(|v| v.abs())
    }
    pub fn dot(&self, other: &Tensor) -> f32 {
        (self.data.clone() * &other.data).sum()
    }
    pub fn max(&self) -> f32 {
        self.data.iter().copied().fold(f32::NEG_INFINITY, f32::max)
    }
    pub fn min(&self) -> f32 {
        self.data.iter().copied().fold(f32::INFINITY, f32::min)
    }
    pub fn sum(&self) -> f32 {
        self.data.iter().sum()
    }
}

impl Add<&Tensor> for &Tensor {
    type Output = Tensor;
    fn add(self, other: &Tensor) -> Tensor {
        self.add(other)
    }
}

impl Add<f32> for &Tensor {
    type Output = Tensor;
    fn add(self, scalar: f32) -> Tensor {
        self.mapv(|v| v + scalar)
    }
}

impl Mul<&Tensor> for &Tensor {
    type Output = Tensor;
    fn mul(self, other: &Tensor) -> Tensor {
        self.mul_elem(other)
    }
}

impl Mul<f32> for &Tensor {
    type Output = Tensor;
    fn mul(self, scalar: f32) -> Tensor {
        self.scale(scalar)
    }
}

impl Sub<&Tensor> for &Tensor {
    type Output = Tensor;
    fn sub(self, other: &Tensor) -> Tensor {
        self.sub(other)
    }
}

impl From<Array2<f32>> for Tensor {
    fn from(data: Array2<f32>) -> Self {
        Self { data }
    }
}

impl From<Tensor> for Array2<f32> {
    fn from(tensor: Tensor) -> Self {
        tensor.data
    }
}

impl Tensor {
    pub(crate) fn to_ndarray(&self) -> &ndarray::Array2<f32> {
        &self.data
    }
    pub(crate) fn to_ndarray_mut(&mut self) -> &mut ndarray::Array2<f32> {
        &mut self.data
    }
}
