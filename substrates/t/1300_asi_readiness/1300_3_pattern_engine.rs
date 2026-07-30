// ═══════════════════════════════════════════════════════════════════════════════
// 1300_3_pattern_engine.rs — Substrato 1300.3: PatternEngine com Cache Deslizante
// Selo: CATHEDRAL-1300.3-PATTERN-ENGINE-v1.0.0-2026-06-13
// Arquiteto: ORCID 0009-0005-2697-4668
// ═══════════════════════════════════════════════════════════════════════

#![no_std]
#![forbid(unsafe_code)]

extern crate alloc;

use alloc::vec::Vec;
use alloc::collections::VecDeque;

/// Configuração do cache deslizante
#[derive(Debug, Clone, Copy)]
pub struct CacheConfig {
    pub window_size: usize,
    pub max_patterns: usize,
}

impl Default for CacheConfig {
    fn default() -> Self {
        Self {
            window_size: 1024,
            max_patterns: 100,
        }
    }
}

/// Representa um padrão detectado no fluxo de tokens/eventos
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pattern {
    pub id: u64,
    pub sequence: Vec<u8>,
    pub frequency: usize,
    pub coherence_score: u32,
}

/// Cache deslizante que mantém os padrões mais recentes e relevantes
#[derive(Debug)]
pub struct SlidingCache {
    config: CacheConfig,
    recent_events: VecDeque<u8>,
    known_patterns: Vec<Pattern>,
    event_count: u64,
}

impl SlidingCache {
    pub fn new(config: CacheConfig) -> Self {
        Self {
            config,
            recent_events: VecDeque::with_capacity(config.window_size),
            known_patterns: Vec::new(),
            event_count: 0,
        }
    }

    /// Adiciona um novo evento e atualiza a janela deslizante
    pub fn push_event(&mut self, event: u8) {
        if self.recent_events.len() >= self.config.window_size {
            self.recent_events.pop_front();
        }
        self.recent_events.push_back(event);
        self.event_count += 1;

        self.extract_patterns();
    }

    /// Lógica heurística simplificada (no_std) para extração de padrões
    fn extract_patterns(&mut self) {
        if self.recent_events.len() < 4 {
            return; // Precisa de pelo menos 4 eventos para formar um padrão relevante
        }

        // Exemplo simplificado: procura por sequências repetidas recentes (tamanho 4)
        let len = self.recent_events.len();
        let current_seq: Vec<u8> = self.recent_events.iter().skip(len - 4).copied().collect();

        // Verifica se a sequência já é conhecida
        let mut found = false;
        for pattern in &mut self.known_patterns {
            if pattern.sequence == current_seq {
                pattern.frequency += 1;
                pattern.coherence_score = pattern.coherence_score.saturating_add(10);
                found = true;
                break;
            }
        }

        // Se for nova e tivermos espaço ou quisermos substituir a de menor score
        if !found {
            if self.known_patterns.len() < self.config.max_patterns {
                self.known_patterns.push(Pattern {
                    id: self.event_count,
                    sequence: current_seq,
                    frequency: 1,
                    coherence_score: 10,
                });
            } else {
                // Substitui a de menor coerência
                if let Some(min_idx) = self.known_patterns.iter().enumerate().min_by_key(|(_, p)| p.coherence_score).map(|(i, _)| i) {
                    // Península de decaimento: só substitui se a nova for "potencialmente melhor"
                    // (aqui simplificado para substituição direta do pior)
                    self.known_patterns[min_idx] = Pattern {
                        id: self.event_count,
                        sequence: current_seq,
                        frequency: 1,
                        coherence_score: 10,
                    };
                }
            }
        }
    }

    pub fn get_top_patterns(&self, k: usize) -> Vec<Pattern> {
        let mut sorted = self.known_patterns.clone();
        // Ordena por score de coerência, decrescente
        sorted.sort_by(|a, b| b.coherence_score.cmp(&a.coherence_score));
        sorted.into_iter().take(k).collect()
    }

    pub fn clear(&mut self) {
        self.recent_events.clear();
        self.known_patterns.clear();
        self.event_count = 0;
    }
}

/// Motor principal de reconhecimento determinístico
pub struct PatternEngine {
    pub cache: SlidingCache,
}

impl PatternEngine {
    pub fn new() -> Self {
        Self {
            cache: SlidingCache::new(CacheConfig::default()),
        }
    }

    pub fn with_config(config: CacheConfig) -> Self {
        Self {
            cache: SlidingCache::new(config),
        }
    }

    pub fn process_stream(&mut self, stream: &[u8]) {
        for &event in stream {
            self.cache.push_event(event);
        }
    }

    pub fn top_patterns(&self, k: usize) -> Vec<Pattern> {
        self.cache.get_top_patterns(k)
    }
}

// ============================================================================
// Testes
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sliding_cache_eviction() {
        let config = CacheConfig {
            window_size: 5,
            max_patterns: 10,
        };
        let mut cache = SlidingCache::new(config);

        for i in 0..10 {
            cache.push_event(i as u8);
        }

        assert_eq!(cache.recent_events.len(), 5);
        // O cache deve conter os últimos 5 elementos (5, 6, 7, 8, 9)
        assert_eq!(cache.recent_events.back().copied(), Some(9));
        assert_eq!(cache.recent_events.front().copied(), Some(5));
    }

    #[test]
    fn test_pattern_extraction_and_scoring() {
        let mut engine = PatternEngine::new();

        // Sequência repetida: 1, 2, 3, 4
        let stream = [1, 2, 3, 4, 5, 1, 2, 3, 4, 6, 1, 2, 3, 4];
        engine.process_stream(&stream);

        let top = engine.top_patterns(1);
        assert!(!top.is_empty());
        assert_eq!(top[0].sequence, alloc::vec![1, 2, 3, 4]);
        assert_eq!(top[0].frequency, 3);
        assert_eq!(top[0].coherence_score, 30);
    }
}
