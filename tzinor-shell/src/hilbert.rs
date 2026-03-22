//! Hilbert Curve 3D Visualization
//!
//! Implements 3D Hilbert curve rendering for the HilbertFS filesystem
//! and Q-Mesh network visualization.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HilbertPoint {
    pub index: u64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub distance_from_origin: f64,
}

pub struct HilbertCurve3D {
    pub order: u32,
    pub size: u64,
    pub points: Vec<HilbertPoint>,
}

impl HilbertCurve3D {
    pub fn new(order: u32) -> Self {
        let size = 2u64.pow(order);
        let total_points = size * size * size;
        let mut points = Vec::with_capacity(total_points as usize);

        for i in 0..total_points {
            let (x, y, z) = Self::index_to_xyz(i, order);
            let distance = ((x * x + y * y + z * z) as f64).sqrt();

            points.push(HilbertPoint {
                index: i,
                x: x as f64 / (size - 1) as f64,
                y: y as f64 / (size - 1) as f64,
                z: z as f64 / (size - 1) as f64,
                distance_from_origin: distance / ((3.0_f64).sqrt()),
            });
        }

        Self {
            order,
            size,
            points,
        }
    }

    /// Convert Hilbert index to 3D coordinates
    fn index_to_xyz(index: u64, order: u32) -> (u64, u64, u64) {
        let size = 2u64.pow(order);

        // Simplified 3D Morton-to-Hilbert conversion
        // In a full implementation, this would use the proper Hilbert curve algorithm

        let mut x = 0u64;
        let mut y = 0u64;
        let mut z = 0u64;

        for bit in 0..order {
            let mask = 1u64 << bit;

            if index & mask != 0 {
                x |= mask;
            }
            if (index >> order) & mask != 0 {
                y |= mask;
            }
            if (index >> (2 * order)) & mask != 0 {
                z |= mask;
            }
        }

        (x, y, z)
    }

    pub fn render_ascii(&self, slice_z: Option<f64>) {
        let grid_size = 40;
        let mut grid = vec![vec![' '; grid_size]; grid_size];

        for point in &self.points {
            let z_target = slice_z.unwrap_or(0.5);

            // Show slice at given z
            if let Some(z) = slice_z {
                if (point.z - z).abs() > 0.05 {
                    continue;
                }
            }

            let px = ((point.x * (grid_size - 1) as f64) as usize).min(grid_size - 1);
            let py = ((point.y * (grid_size - 1) as f64) as usize).min(grid_size - 1);

            let idx = (py * grid_size + px) as usize;
            if idx < grid_size * grid_size {
                grid[idx / grid_size][idx % grid_size] = '█';
            }
        }

        println!("╔══════════════════════════════════════╗");
        println!("║  HILBERT CURVE 3D - ORDER {}              ║", self.order);
        if let Some(z) = slice_z {
            println!("║  Slice at z = {:.2}                        ║", z);
        }
        println!("╠══════════════════════════════════════╣");

        for row in &grid {
            print!("║ ");
            for &c in row {
                print!("{}", c);
            }
            println!(" ║");
        }

        println!("╚══════════════════════════════════════╝");
    }

    pub fn render_connected_ascii(&self, max_points: usize) {
        let display_points: Vec<_> = self.points.iter().take(max_points).collect();

        if display_points.is_empty() {
            return;
        }

        println!("╔══════════════════════════════════════╗");
        println!(
            "║  HILBERT CURVE ({} points)              ║",
            display_points.len()
        );
        println!("╠══════════════════════════════════════╣");

        let scale = 38.0;

        for point in display_points {
            let x = (point.x * scale + 20.0) as usize;
            let y = (point.y * scale + 10.0) as usize;

            if x < 40 && y < 20 {
                print!("\x1B[{};{}H●", y + 1, x + 1);
            }
        }

        println!("\n╚══════════════════════════════════════╝");
    }

    pub fn local_neighborhood(&self, center_index: u64, radius: u64) -> Vec<&HilbertPoint> {
        let center = match self.points.iter().find(|p| p.index == center_index) {
            Some(p) => p,
            None => return vec![],
        };

        self.points
            .iter()
            .filter(|p| {
                let dx = p.x - center.x;
                let dy = p.y - center.y;
                let dz = p.z - center.z;
                let dist = (dx * dx + dy * dy + dz * dz).sqrt();
                dist <= radius as f64 / 100.0
            })
            .collect()
    }

    pub fn path_length(&self, from: u64, to: u64) -> u64 {
        if from > to {
            return to.saturating_sub(from);
        } else {
            return to - from;
        }
    }
}

impl Default for HilbertCurve3D {
    fn default() -> Self {
        Self::new(3) // Order 3 = 512 nodes
    }
}
