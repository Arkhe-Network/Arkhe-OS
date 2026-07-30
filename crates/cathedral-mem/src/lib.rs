pub mod plurality_adapter;
pub mod backend {
    use super::plurality_adapter::MemoryBlock;
    pub enum MemoryError {
        External(String),
        NotImplemented(String),
    }
    pub struct BackendStats {
        pub total_blocks: usize,
        pub total_bytes: usize,
        pub cache_hits: u64,
        pub cache_misses: u64,
        pub avg_read_latency_ms: u64,
        pub avg_write_latency_ms: u64,
    }
    pub type Result<T> = std::result::Result<T, MemoryError>;
}
