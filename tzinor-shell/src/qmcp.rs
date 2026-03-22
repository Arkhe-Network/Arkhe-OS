//! Q-MCP (Quantum Message Communication Protocol)
//!
//! Network protocol for quantum mesh communication.
//! Implements Hilbert curve FMM (Fast Multipole Method) routing.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QMeshNode {
    pub id: u32,
    pub position: (f64, f64, f64),
    pub phase: f64,
    pub coherence: f64,
    pub neighbors: Vec<u32>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QMeshNetwork {
    pub nodes: HashMap<u32, QMeshNode>,
    pub order: u32,
    pub total_nodes: u32,
}

impl QMeshNetwork {
    pub fn new(order: u32) -> Self {
        let total_nodes = 2u32.pow(order * 3);
        let mut nodes = HashMap::new();

        // Create Hilbert curve nodes
        for i in 0..total_nodes {
            let pos = Self::hilbert_position(i, order);
            nodes.insert(
                i,
                QMeshNode {
                    id: i,
                    position: pos,
                    phase: 0.0,
                    coherence: 1.0,
                    neighbors: Self::hilbert_neighbors(i, order),
                    is_active: true,
                },
            );
        }

        Self {
            nodes,
            order,
            total_nodes,
        }
    }

    /// Convert Hilbert index to 3D position
    fn hilbert_position(index: u32, order: u32) -> (f64, f64, f64) {
        let size = 2u32.pow(order) as f64;
        let max_val = size - 1.0;

        // Simplified Hilbert curve mapping
        let x = (index % size as u32) as f64 / max_val;
        let y = ((index / size as u32) % size as u32) as f64 / max_val;
        let z = (index / (size * size) as u32) as f64 / max_val;

        (x, y, z)
    }

    /// Get neighbors in Hilbert curve
    fn hilbert_neighbors(index: u32, _order: u32) -> Vec<u32> {
        let mut neighbors = Vec::new();

        // Previous node
        if index > 0 {
            neighbors.push(index - 1);
        }

        // Next node
        let max_index = 2u32.pow(_order * 3) - 1;
        if index < max_index {
            neighbors.push(index + 1);
        }

        neighbors
    }

    pub fn get_node(&self, id: u32) -> Option<&QMeshNode> {
        self.nodes.get(&id)
    }

    pub fn set_node_phase(&mut self, id: u32, phase: f64) -> Result<()> {
        if let Some(node) = self.nodes.get_mut(&id) {
            node.phase = phase;
            Ok(())
        } else {
            Err(anyhow::anyhow!("Node {} not found", id))
        }
    }

    pub fn calculate_impedance(&self, from: u32, to: u32) -> f64 {
        let from_node = match self.nodes.get(&from) {
            Some(n) => n,
            None => return f64::MAX,
        };

        let to_node = match self.nodes.get(&to) {
            Some(n) => n,
            None => return f64::MAX,
        };

        // Calculate phase impedance
        let dx = from_node.position.0 - to_node.position.0;
        let dy = from_node.position.1 - to_node.position.1;
        let dz = from_node.position.2 - to_node.position.2;
        let distance = (dx * dx + dy * dy + dz * dz).sqrt();

        // Phase difference
        let dphi = from_node.phase - to_node.phase;

        // Impedance = distance + phase coupling
        distance + dphi.abs() * 0.1
    }

    pub fn route_fmm(&self, from: u32, to: u32) -> Vec<u32> {
        let mut path = vec![from];
        let mut current = from;

        while current != to {
            let current_node = match self.nodes.get(&current) {
                Some(n) => n,
                None => break,
            };

            // Find neighbor closest to target
            let mut best_next = current;
            let mut best_distance = f64::MAX;

            for &neighbor in &current_node.neighbors {
                let dist = self.calculate_impedance(neighbor, to);
                if dist < best_distance {
                    best_distance = dist;
                    best_next = neighbor;
                }
            }

            if best_next == current {
                break; // Stuck
            }

            current = best_next;
            path.push(current);
        }

        path
    }

    pub fn visualize(&self) {
        println!("╔══════════════════════════════════════════════════════╗");
        println!(
            "║  Q-MESH NETWORK TOPOLOGY (Hilbert Curve Order {})        ║",
            self.order
        );
        println!("╠══════════════════════════════════════════════════════╣");
        println!("║  Total nodes: {:<44}║", self.total_nodes);
        println!("╠══════════════════════════════════════════════════════╣");

        // Show first 10 and last 10 nodes
        let display_nodes: Vec<u32> = (0..self.total_nodes.min(20)).collect();

        for &id in &display_nodes {
            if let Some(node) = self.nodes.get(&id) {
                let status = if node.is_active { "●" } else { "○" };
                let coherence_bar = Self::coherence_bar(node.coherence);
                println!(
                    "║  Node {:>4}: ({:>5.2}, {:>5.2}, {:>5.2}) {} {}  ║",
                    id, node.position.0, node.position.1, node.position.2, status, coherence_bar
                );
            }
        }

        if self.total_nodes > 20 {
            println!(
                "║                        ... {} more nodes ...                 ║",
                self.total_nodes - 20
            );
        }

        println!("╚══════════════════════════════════════════════════════╝");
    }

    fn coherence_bar(coherence: f64) -> String {
        let filled = (coherence * 10.0).round() as usize;
        let empty = 10 - filled;
        format!("[{}{}]", "█".repeat(filled), "░".repeat(empty))
    }

    pub fn network_stats(&self) -> serde_json::Value {
        let active_nodes = self.nodes.values().filter(|n| n.is_active).count();
        let avg_coherence =
            self.nodes.values().map(|n| n.coherence).sum::<f64>() / self.total_nodes as f64;

        serde_json::json!({
            "total_nodes": self.total_nodes,
            "active_nodes": active_nodes,
            "order": self.order,
            "average_coherence": avg_coherence,
        })
    }
}
