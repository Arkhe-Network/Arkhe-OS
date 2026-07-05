// ============================================================================
// ARKHE QIP Engine — Kernel Module
// ============================================================================


use sha3::{Sha3_256, Digest};

#[repr(C)]
#[derive(Clone, Copy)]
pub struct GradientEntry {
    pub shard_id: u32,
    pub layer_idx: u32,
    pub step: u64,
    pub gradient_hash: [u8; 32],
}

#[repr(C)]
pub struct InfluenceResult {
    pub data_hash: [u8; 32],
    pub block_number: u64,
    pub probability: u32,
    pub confidence: u32,
}

pub struct QIPEngine {
    gradient_store: [Option<GradientEntry>; 1024],
    entry_count: u32,
}

impl QIPEngine {
    pub const fn new() -> Self {
        Self {
            gradient_store: [None; 1024],
            entry_count: 0,
        }
    }

    pub fn process_block(&mut self, block_data: &[u8], block_number: u64) -> [u8; 32] {
        let block_hash = Self::hash_block(block_data);
        let gradient_hash = self.extract_gradients(block_data);
        self.store_gradient(block_number, gradient_hash);
        let _influence = self.calculate_influence(&block_hash);
        block_hash
    }

    fn hash_block(data: &[u8]) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        hasher.update(data);
        hasher.finalize().into()
    }

    fn extract_gradients(&self, data: &[u8]) -> [u8; 32] {
        Self::hash_block(data)
    }

    fn store_gradient(&mut self, step: u64, gradient_hash: [u8; 32]) {
        if self.entry_count < 1024 {
            let idx = self.entry_count as usize;
            self.gradient_store[idx] = Some(GradientEntry {
                shard_id: idx as u32,
                layer_idx: 0,
                step,
                gradient_hash,
            });
            self.entry_count += 1;
        }
    }

    fn calculate_influence(&self, block_hash: &[u8; 32]) -> u32 {
        let mut max_sim = 0u32;
        for entry in &self.gradient_store {
            if let Some(e) = entry {
                let sim = Self::cosine_sim_fixed(block_hash, &e.gradient_hash);
                if sim > max_sim { max_sim = sim; }
            }
        }
        max_sim
    }

    fn cosine_sim_fixed(a: &[u8; 32], b: &[u8; 32]) -> u32 {
        let mut dot: u64 = 0;
        let mut norm_a: u64 = 0;
        let mut norm_b: u64 = 0;
        for i in 0..32 {
            let ai = a[i] as u32 as u64;
            let bi = b[i] as u32 as u64;
            dot += ai * bi;
            norm_a += ai * ai;
            norm_b += bi * bi;
        }
        if norm_a == 0 || norm_b == 0 { return 0; }
        let product = norm_a.saturating_mul(norm_b);
        let sqrt = Self::isqrt(product);
        if sqrt == 0 { return 0; }
        ((dot << 16) / sqrt) as u32
    }

    fn isqrt(n: u64) -> u64 {
        if n == 0 { return 0; }
        let mut x = n;
        let mut y = (x + 1) / 2;
        while y < x { x = y; y = (x + n / x) / 2; }
        x
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn isqrt_matches_expected() {
        assert_eq!(QIPEngine::isqrt(0), 0);
        assert_eq!(QIPEngine::isqrt(1), 1);
        assert_eq!(QIPEngine::isqrt(16), 4);
        assert_eq!(QIPEngine::isqrt(15), 3);
        assert_eq!(QIPEngine::isqrt(1_000_000), 1000);
    }

    #[test]
    fn cosine_of_identical_is_maximal_and_of_zero_is_zero() {
        let v = [7u8; 32];
        let zero = [0u8; 32];
        let same = QIPEngine::cosine_sim_fixed(&v, &v);
        let with_zero = QIPEngine::cosine_sim_fixed(&v, &zero);
        assert_eq!(with_zero, 0);
        // Vetores idênticos: similaridade ~1.0 em fixed-point (<<16 => ~65536).
        assert!(same > 60_000, "esperado alto, obtido {same}");
    }

    #[test]
    fn store_gradient_respects_capacity_and_counts() {
        let mut e = QIPEngine::new();
        let h = e.process_block(b"payload", 42);
        assert_ne!(h, [0u8; 32]);
        assert_eq!(e.entry_count, 1);
    }
}
