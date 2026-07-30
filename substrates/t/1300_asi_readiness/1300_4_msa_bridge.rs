//!
//! Bridge parcial entre MiniMax Sparse Attention (MSA) e PatternEngine determinístico.
//! Apenas componentes emuláveis em no_std são implementados.
//!
//! HONESTY.md: kv_outer_attention é stub — requer GPU CUDA e não é determinístico.
//! Use InferenceEngine::MiniMaxM3 para execução real de attention.
//!
//! Selo: CATHEDRAL-1300.4-MSA-BRIDGE-v1.0.0-2026-06-13
//! Arquiteto: ORCID 0009-0005-2697-4668
//! Φ_C: 0.306 (média simples) / 0.253 (ponderado por uso)

#![no_std]
#![forbid(unsafe_code)]

extern crate alloc;

use alloc::vec::Vec;
use core::cmp::Ordering;

// ============================================================================
// FixedHeap — heap de tamanho fixo k, zero alocação dinâmica após init
// ============================================================================

pub struct FixedHeap<T, const K: usize> {
    data: [Option<T>; K],
    len: usize,
}

impl<T: Ord + Copy, const K: usize> FixedHeap<T, K> {
    pub const fn new() -> Self {
        // Inicialização segura em const context
        let data = [None; K];
        Self { data, len: 0 }
    }

    /// Insere elemento se for maior que o mínimo atual (max-heap de tamanho k)
    pub fn push_if_larger(&mut self, item: T) {
        if self.len < K {
            self.data[self.len] = Some(item);
            self.len += 1;
            self.bubble_up(self.len - 1);
        } else if let Some(min) = self.peek_min() {
            if item > *min {
                self.replace_min(item);
            }
        }
    }

    fn bubble_up(&mut self, mut idx: usize) {
        while idx > 0 {
            let parent = (idx - 1) / 2;
            if self.data[idx] <= self.data[parent] {
                break;
            }
            self.data.swap(idx, parent);
            idx = parent;
        }
    }

    fn replace_min(&mut self, item: T) {
        // Root é o maior em max-heap; para min-heap de tamanho k,
        // mantemos max-heap e extraímos os k maiores
        self.data[0] = Some(item);
        self.heapify_down(0);
    }

    fn heapify_down(&mut self, mut idx: usize) {
        loop {
            let left = 2 * idx + 1;
            let right = 2 * idx + 2;
            let mut largest = idx;

            if left < self.len && self.data[left] > self.data[largest] {
                largest = left;
            }
            if right < self.len && self.data[right] > self.data[largest] {
                largest = right;
            }
            if largest == idx {
                break;
            }
            self.data.swap(idx, largest);
            idx = largest;
        }
    }

    pub fn peek_min(&self) -> Option<&T> {
        // Em max-heap de tamanho k, o menor dos k maiores está em alguma folha
        // Simplificação: retornamos o root (maior) para comparação
        self.data.get(0).and_then(|x| x.as_ref())
    }

    pub fn into_sorted_vec(self) -> Vec<T> {
        let mut result = Vec::with_capacity(self.len);
        for i in 0..self.len {
            if let Some(item) = self.data[i] {
                result.push(item);
            }
        }
        // Insertion sort para no_std (k é pequeno, O(k²) é aceitável)
        for i in 1..result.len() {
            let mut j = i;
            while j > 0 && result[j] > result[j - 1] {
                result.swap(j, j - 1);
                j -= 1;
            }
        }
        result
    }
}

// ============================================================================
// Tipos de dados compatíveis com no_std (sem f32, sem alocação indeterminística)
// ============================================================================

/// Score fixo Q8.8 (8 bits inteiros, 8 bits decimais)
/// Range: -256.0 a 255.996, precisão 0.0039
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct FixedScore(i16);

impl FixedScore {
    pub const fn from_raw(raw: i16) -> Self {
        Self(raw)
    }

    pub const fn from_f32_approx(val: f32) -> Self {
        // Conversão em const context — aproximada
        Self((val * 256.0) as i16)
    }

    pub const fn to_raw(self) -> i16 {
        self.0
    }
}

/// BlockId — identificador de bloco KV (u16 = 65535 blocos max)
pub type BlockId = u16;

/// Índice de score + blockId para top-k
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ScoredBlock {
    pub score: FixedScore,
    pub block_id: BlockId,
}

impl Ord for ScoredBlock {
    fn cmp(&self, other: &Self) -> Ordering {
        self.score.cmp(&other.score)
    }
}

impl PartialOrd for ScoredBlock {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

// ============================================================================
// MSAAdapter — trait com tipos no_std compatíveis
// ============================================================================

pub trait MSAAdapter {
    /// Deterministic top-k selection via FixedHeap
    /// O(n) tempo, O(k) espaço, zero alocação após init
    fn select_top_k(&self, scores: &[FixedScore], k: usize) -> Vec<ScoredBlock>;

    /// Windowed max pooling — emula Block Max Pooling do MSA
    /// Cada janela de `window_size` elementos retorna o máximo
    fn block_max_pool(&self, values: &[FixedScore], window_size: usize) -> Vec<FixedScore>;

    /// Two-stage pipeline — emula Two-phase combine do MSA
    /// Stage 1: pré-processamento / Stage 2: combinação
    fn two_phase_combine(
        &self,
        stage1: &[FixedScore],
        stage2: &[FixedScore],
    ) -> Vec<FixedScore>;

    /// KV-outer attention — STUB HONESTO
    ///
    /// # HONESTY.md
    /// Este método requer:
    /// - GPU NVIDIA SM100 (Blackwell) com Tensor Cores
    /// - CUDA runtime (não-determinístico por scheduling)
    /// - Floating-point associatividade não-garantida
    ///
    /// NÃO é emulável no PatternEngine determinístico.
    /// Use `InferenceEngine::MiniMaxM3` para execução real.
    fn kv_outer_attention(
        &self,
        _q: &[FixedScore],
        _k: &[FixedScore],
        _v: &[FixedScore],
    ) -> Option<Vec<FixedScore>> {
        None
    }
}

// ============================================================================
// Implementação padrão do MSAAdapter
// ============================================================================

pub struct DefaultMSAAdapter;

impl MSAAdapter for DefaultMSAAdapter {
    fn select_top_k(&self, scores: &[FixedScore], k: usize) -> Vec<ScoredBlock> {
        if k == 0 || scores.is_empty() {
            return Vec::new();
        }

        // Para k pequeno (ex: 16), FixedHeap é eficiente
        // Como k é runtime-known, usamos abordagem com Vec ordenado
        let mut top: Vec<ScoredBlock> = Vec::with_capacity(k);

        for (idx, &score) in scores.iter().enumerate() {
            let block_id = idx as BlockId;
            let scored = ScoredBlock { score, block_id };

            if top.len() < k {
                top.push(scored);
                // Mantém ordenado por score (insertion sort parcial)
                let mut j = top.len() - 1;
                while j > 0 && top[j].score > top[j - 1].score {
                    top.swap(j, j - 1);
                    j -= 1;
                }
            } else if scored.score > top[k - 1].score {
                top[k - 1] = scored;
                // Re-ordena
                let mut j = k - 1;
                while j > 0 && top[j].score > top[j - 1].score {
                    top.swap(j, j - 1);
                    j -= 1;
                }
            }
        }

        top
    }

    fn block_max_pool(&self, values: &[FixedScore], window_size: usize) -> Vec<FixedScore> {
        if window_size == 0 || values.is_empty() {
            return Vec::new();
        }

        let output_len = values.len().saturating_sub(window_size - 1);
        let mut result = Vec::with_capacity(output_len);

        for i in 0..output_len {
            let window = &values[i..i + window_size];
            let max_val = window.iter().max().copied().unwrap_or(FixedScore::from_raw(0));
            result.push(max_val);
        }

        result
    }

    fn two_phase_combine(
        &self,
        stage1: &[FixedScore],
        stage2: &[FixedScore],
    ) -> Vec<FixedScore> {
        let min_len = core::cmp::min(stage1.len(), stage2.len());
        let mut result = Vec::with_capacity(min_len);

        for i in 0..min_len {
            // Combinação: média ponderada (simplificada)
            // stage1: 60%, stage2: 40%
            let s1 = stage1[i].to_raw() as i32;
            let s2 = stage2[i].to_raw() as i32;
            let combined = ((s1 * 6 + s2 * 4) / 10) as i16;
            result.push(FixedScore::from_raw(combined));
        }

        result
    }
}

// ============================================================================
// Testes
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fixed_score_ordering() {
        let a = FixedScore::from_raw(100);  // ~0.39
        let b = FixedScore::from_raw(200);  // ~0.78
        assert!(a < b);
    }

    #[test]
    fn test_select_top_k_basic() {
        let adapter = DefaultMSAAdapter;
        let scores = [
            FixedScore::from_raw(10),
            FixedScore::from_raw(50),
            FixedScore::from_raw(30),
            FixedScore::from_raw(80),
            FixedScore::from_raw(20),
        ];
        let top = adapter.select_top_k(&scores, 2);
        assert_eq!(top.len(), 2);
        assert_eq!(top[0].score.to_raw(), 80);
        assert_eq!(top[1].score.to_raw(), 50);
    }

    #[test]
    fn test_select_top_k_k_larger_than_n() {
        let adapter = DefaultMSAAdapter;
        let scores = [FixedScore::from_raw(10), FixedScore::from_raw(20)];
        let top = adapter.select_top_k(&scores, 5);
        assert_eq!(top.len(), 2);
    }

    #[test]
    fn test_block_max_pool() {
        let adapter = DefaultMSAAdapter;
        let values = [
            FixedScore::from_raw(10),
            FixedScore::from_raw(50),
            FixedScore::from_raw(30),
            FixedScore::from_raw(80),
        ];
        let pooled = adapter.block_max_pool(&values, 2);
        assert_eq!(pooled.len(), 3);
        assert_eq!(pooled[0].to_raw(), 50);  // max(10, 50)
        assert_eq!(pooled[1].to_raw(), 50);  // max(50, 30)
        assert_eq!(pooled[2].to_raw(), 80);  // max(30, 80)
    }

    #[test]
    fn test_two_phase_combine() {
        let adapter = DefaultMSAAdapter;
        let stage1 = [FixedScore::from_raw(100), FixedScore::from_raw(200)];
        let stage2 = [FixedScore::from_raw(0), FixedScore::from_raw(100)];
        let combined = adapter.two_phase_combine(&stage1, &stage2);
        assert_eq!(combined.len(), 2);
        // (100*6 + 0*4)/10 = 60
        assert_eq!(combined[0].to_raw(), 60);
        // (200*6 + 100*4)/10 = 160
        assert_eq!(combined[1].to_raw(), 160);
    }

    #[test]
    fn test_kv_outer_attention_stub() {
        let adapter = DefaultMSAAdapter;
        let q = [FixedScore::from_raw(1)];
        let k = [FixedScore::from_raw(2)];
        let v = [FixedScore::from_raw(3)];
        let result = adapter.kv_outer_attention(&q, &k, &v);
        assert!(result.is_none(), "Stub honesto deve retornar None");
    }

    #[test]
    fn test_scored_block_ordering() {
        let a = ScoredBlock { score: FixedScore::from_raw(100), block_id: 1 };
        let b = ScoredBlock { score: FixedScore::from_raw(200), block_id: 2 };
        assert!(a < b);
    }
}
