// ============================================================================
// ARKHE Q-Art Engine — Kernel Module
// ============================================================================



#[repr(u8)]
#[derive(Clone, Copy)]
pub enum ArtBlockType {
    Visual = 0,
    Musical = 1,
    Literary = 2,
    Generative = 3,
}

#[repr(C, packed)]
#[derive(Clone, Copy)]
pub struct ArtBlockHeader {
    pub magic: [u8; 4],
    pub version: u16,
    pub block_type: ArtBlockType,
    pub timestamp_ns: u64,
    pub data_length: u32,
    pub style_embedding_offset: u32,
    pub perceptual_hash_offset: u32,
}

impl ArtBlockHeader {
    pub fn is_valid(&self) -> bool {
        self.magic == [b'A', b'R', b'T', 0]
    }
}

pub struct QArtEngine {
    pub registered_artworks: u64,
    pub total_royalties: u64,
}

impl QArtEngine {
    pub const fn new() -> Self {
        Self {
            registered_artworks: 0,
            total_royalties: 0,
        }
    }

    pub fn process_art_block(&mut self, data: &[u8], block_number: u64) -> Option<ArtBlockHeader> {
        if data.len() < core::mem::size_of::<ArtBlockHeader>() {
            return None;
        }

        let header: &ArtBlockHeader = unsafe { &*(data.as_ptr() as *const ArtBlockHeader) };
        if !header.is_valid() {
            return None;
        }

        self.registered_artworks += 1;

        let royalty = match header.block_type {
            ArtBlockType::Visual => 100,
            ArtBlockType::Musical => 150,
            ArtBlockType::Literary => 80,
            ArtBlockType::Generative => 120,
        };

        self.total_royalties += royalty as u64;
        Some(*header)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn art_bytes(block_type: u8) -> [u8; 32] {
        let mut b = [0u8; 32];
        b[0..4].copy_from_slice(&[b'A', b'R', b'T', 0]);
        b[6] = block_type; // offset do campo block_type no header packed
        b
    }

    #[test]
    fn rejects_non_art_and_short_input() {
        let mut e = QArtEngine::new();
        assert!(e.process_art_block(b"no", 0).is_none());
        let mut bad = [0u8; 32];
        bad[0..4].copy_from_slice(&[b'X', b'X', b'X', b'X']);
        assert!(e.process_art_block(&bad, 0).is_none());
        assert_eq!(e.registered_artworks, 0);
    }

    #[test]
    fn accepts_valid_art_and_accrues_royalty() {
        let mut e = QArtEngine::new();
        let out = e.process_art_block(&art_bytes(0), 1); // Visual => 100
        assert!(out.is_some());
        assert_eq!(e.registered_artworks, 1);
        assert_eq!(e.total_royalties, 100);
    }
}
