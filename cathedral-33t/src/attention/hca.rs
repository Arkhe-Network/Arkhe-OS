use crate::tensor::Tensor; use crate::config::AttentionConfig;
pub struct HeavilyCompressedAttention { num_heads: usize, head_dim: usize, compression_ratio: usize, chunk_size: usize, }
impl HeavilyCompressedAttention {
    pub fn new(config: &AttentionConfig) -> Self { Self { num_heads: config.num_heads, head_dim: config.head_dim, compression_ratio: config.hca_compression, chunk_size: 128, } }
    pub fn forward(&self, x: &Tensor, _kv_cache: Option<&Tensor>) -> Tensor { let seq_len = x.shape()[0]; let num_chunks = (seq_len + self.chunk_size - 1) / self.chunk_size; let mut outputs = Vec::new(); for i in 0..num_chunks { let start = i * self.chunk_size; let end = ((i + 1) * self.chunk_size).min(seq_len); let chunk = x.slice_axis(0, start); let compressed = chunk.scale(1.0 / self.compression_ratio as f32); outputs.push(compressed); } Tensor::concat(&outputs.iter().collect::<Vec<_>>(), 0) }
}
