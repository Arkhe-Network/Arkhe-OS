pub struct MerkleProof {}

pub struct MerkleTree {
    hashes: Vec<[u8; 32]>,
}

impl Default for MerkleTree {
    fn default() -> Self {
        Self::new()
    }
}

impl MerkleTree {
    pub fn new() -> Self {
        Self { hashes: Vec::new() }
    }

    pub fn push(&mut self, hash: [u8; 32]) {
        self.hashes.push(hash);
    }

    pub fn root(&self) -> Option<[u8; 32]> {
        self.hashes.last().copied()
    }

    pub fn prove(&self, _index: usize) -> Option<MerkleProof> {
        None
    }
}
