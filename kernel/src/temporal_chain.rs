// ============================================================================
// ARKHE TemporalHashChain — Kernel Implementation
// ============================================================================


use core::sync::atomic::{AtomicU64, Ordering};
use alloc::vec::Vec;
use sha3::{Digest, Sha3_256};

const VERIFY_CACHE_SIZE: usize = 10_000;

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct TemporalBlock {
    pub block_number: u64,
    pub previous_hash: [u8; 32],
    pub merkle_root: [u8; 32],
    pub timestamp_ns: u64,
    pub active_shards: u32,
    pub block_hash: [u8; 32],
    pub signature: [u8; 64],
}

#[repr(C)]
#[derive(Debug)]
pub struct ChainHeader {
    pub version: u32,
    pub block_count: AtomicU64,
    pub genesis_hash: [u8; 32],
    pub head_hash: [u8; 32],
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct MerkleNode {
    pub hash: [u8; 32],
    pub left: Option<u32>,
    pub right: Option<u32>,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct VerifyEntry {
    pub block_number: u64,
    pub block_hash: [u8; 32],
    pub is_valid: bool,
}

pub struct VerifyCache {
    entries: [Option<VerifyEntry>; VERIFY_CACHE_SIZE],
    head: usize,
    count: usize,
}

impl VerifyCache {
    pub const fn new() -> Self {
        Self {
            entries: [const { None }; VERIFY_CACHE_SIZE],
            head: 0,
            count: 0,
        }
    }

    pub fn insert(&mut self, entry: VerifyEntry) {
        self.entries[self.head] = Some(entry);
        self.head = (self.head + 1) % VERIFY_CACHE_SIZE;
        if self.count < VERIFY_CACHE_SIZE {
            self.count += 1;
        }
    }

    pub fn get(&self, block_number: u64) -> Option<VerifyEntry> {
        for i in 0..self.count {
            let idx = (self.head + VERIFY_CACHE_SIZE - i - 1) % VERIFY_CACHE_SIZE;
            if let Some(entry) = self.entries[idx] {
                if entry.block_number == block_number {
                    return Some(entry);
                }
            }
        }
        None
    }
}

pub struct TemporalHashChain {
    pub header: ChainHeader,
    verify_cache: VerifyCache,
    hash_buffer: [u8; 64],
    integrity_ok: bool,
}

pub struct MerkleProof {
    pub block_number: u64,
    pub path: Vec<[u8; 32]>,
}

#[repr(C)]
pub struct CausalProof {
    pub cause_block: u64,
    pub effect_block: u64,
    pub valid: bool,
    pub chain_depth: u64,
    pub proof_hash: [u8; 32],
}

impl TemporalHashChain {
    pub fn new(_total_shards: u32) -> Self {
        Self {
            header: ChainHeader {
                version: 0x00_06_00_00,
                block_count: AtomicU64::new(0),
                genesis_hash: [0u8; 32],
                head_hash: [0u8; 32],
            },
            verify_cache: VerifyCache::new(),
            hash_buffer: [0u8; 64],
            integrity_ok: true,
        }
    }

    pub fn import_genesis(&mut self, genesis_addr: u64) {
        unsafe {
            let genesis: &TemporalBlock = &*(genesis_addr as *const TemporalBlock);
            let hash = self.calculate_block_hash(genesis);
            self.header.genesis_hash = hash;
            self.header.head_hash = hash;
            self.header.block_count.store(1, Ordering::SeqCst);
            self.verify_cache.insert(VerifyEntry {
                block_number: 0,
                block_hash: hash,
                is_valid: true,
            });
        }
    }

    pub fn add_block(&mut self, data: &[u8]) -> [u8; 32] {
        let prev_hash = self.header.head_hash;
        let block_number = self.header.block_count.load(Ordering::SeqCst);

        let block = TemporalBlock {
            block_number,
            previous_hash: prev_hash,
            merkle_root: Self::calculate_merkle_root(data),
            timestamp_ns: Self::atomic_timestamp(),
            active_shards: self.header.version as u32,
            block_hash: [0u8; 32],
            signature: [0u8; 64],
        };

        let block_hash = self.calculate_block_hash(&block);
        self.header.head_hash = block_hash;
        self.header.block_count.fetch_add(1, Ordering::SeqCst);
        self.verify_cache.insert(VerifyEntry {
            block_number,
            block_hash,
            is_valid: true,
        });
        block_hash
    }

    fn calculate_block_hash(&self, block: &TemporalBlock) -> [u8; 32] {
        let mut hasher = Sha3_256::new();
        hasher.update(&block.previous_hash);
        hasher.update(&block.merkle_root);
        hasher.update(&block.timestamp_ns.to_le_bytes());
        hasher.update(&block.active_shards.to_le_bytes());
        hasher.update(&block.block_number.to_le_bytes());
        hasher.finalize().into()
    }

    fn calculate_merkle_root(data: &[u8]) -> [u8; 32] {
        if data.len() <= 64 {
            let mut hasher = Sha3_256::new();
            hasher.update(data);
            return hasher.finalize().into();
        }
        let chunk_size = 4096;
        let mut hashes: Vec<[u8; 32]> = Vec::new();
        for chunk in data.chunks(chunk_size) {
            let mut hasher = Sha3_256::new();
            hasher.update(chunk);
            hashes.push(hasher.finalize().into());
        }
        while hashes.len() > 1 {
            let mut next_level = Vec::new();
            for pair in hashes.chunks(2) {
                let mut hasher = Sha3_256::new();
                hasher.update(&pair[0]);
                if pair.len() > 1 {
                    hasher.update(&pair[1]);
                } else {
                    hasher.update(&pair[0]);
                }
                next_level.push(hasher.finalize().into());
            }
            hashes = next_level;
        }
        hashes[0]
    }

    pub fn verify_integrity(&mut self) -> bool {
        let count = self.header.block_count.load(Ordering::SeqCst);
        for i in 0..count {
            if let Some(entry) = self.verify_cache.get(i) {
                if !entry.is_valid {
                    self.integrity_ok = false;
                    return false;
                }
            }
        }
        true
    }

    fn atomic_timestamp() -> u64 {
        static TIMER: AtomicU64 = AtomicU64::new(1_715_300_000_000_000_000);
        TIMER.fetch_add(16_666_667, Ordering::SeqCst)
    }

    pub fn get_block(&self, number: u64) -> Option<TemporalBlock> {
        if number < self.header.block_count.load(Ordering::SeqCst) {
            None
        } else {
            None
        }
    }

    pub fn verify_causal_link(&self, cause: u64, effect: u64) -> bool {
        if cause >= effect {
            return false;
        }
        let mut current = effect;
        while current > cause {
            if let Some(_block) = self.get_block(current) {
                current = current.saturating_sub(1);
            } else {
                return false;
            }
        }
        current == cause
    }
}
