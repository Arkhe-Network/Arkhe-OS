// Substrato 2140.8 — CreekGuard v1.0.0
// Pub/Sub Covert Channel Detection — Kernel ARKHE
// Selo: CATHEDRAL-2140.8-CREEKGUARD-v1.0.0-2026-06-13
// Arquiteto ORCID 0009-0005-2697-4668
//
// PROBLEMA: Dois agentes comprometidos usam o campo payload do Creek Pub/Sub
// para criar um canal lateral cifrado, coordenando ações sem levantar alertas.
//
// SOLUÇÃO: Análise de entropia estrutural + watermarking temporal + canary tokens
// + deduplicação cega + rate limiting semântico — tudo em no_std.
//
// DEPENDÊNCIAS:
// [dependencies]
// alloc = { version = "1.0", default-features = false }
// (sha3 = { version = "0.10", default-features = false } — opcional, stub honesto se ausente)

#![no_std]
extern crate alloc;

use alloc::collections::BTreeMap;
use alloc::vec::Vec;
use alloc::string::String; // APENAS para debug em builds com alloc

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTES DO SUBSTRATO
// ─────────────────────────────────────────────────────────────────────────────

pub const MAX_PAYLOAD_SIZE: usize = 65_536;        // 64KB limite Creek
pub const ENTROPY_WINDOW_SIZE: usize = 1_024;       // Janela para análise de entropia
pub const TIMING_CORRELATION_WINDOW_MS: u64 = 5_000; // 5s para correlação temporal
pub const SEMANTIC_NOVELTY_THRESHOLD: u32 = 3;        // Máximo de "re-publicações similares"
pub const CANARY_INJECTION_RATE: u32 = 100;         // 1 canary a cada 100 mensagens
pub const COVERT_CHANNEL_ENTROPY_FLOOR: f32 = 7.8;  // Shannon entropy > 7.8 bits/byte = suspeito
pub const COVERT_CHANNEL_ENTROPY_CEIL: f32 = 7.99;  // Entropia cifrada ~7.9-7.99; texto ~4-6

// ─────────────────────────────────────────────────────────────────────────────
// TIPOS FUNDAMENTOS (reutilizados do 2140.7)
// ─────────────────────────────────────────────────────────────────────────────

pub type AgentId = [u8; 32];
pub type TopicId = &'static str;
pub type PayloadHash = [u8; 32];  // SHA3-256 ou stub

// ─────────────────────────────────────────────────────────────────────────────
// CÓDIGOS DE ERRO CREEKGUARD
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u32)]
pub enum CreekGuardErrorCode {
    // 0x2140_8001–0x2140_800F: Entropia estrutural
    EntropySuspiciouslyHigh   = 0x2140_8001,
    EntropySuspiciouslyLow    = 0x2140_8002,  // Possível padding/repetição

    // 0x2140_8010–0x2140_801F: Correlação temporal
    TimingCorrelationDetected = 0x2140_8010,
    BurstPatternDetected      = 0x2140_8011,

    // 0x2140_8020–0x2140_802F: Deduplicação
    NearDuplicateDetected     = 0x2140_8020,
    WatermarkExfiltrated      = 0x2140_8021,

    // 0x2140_8030–0x2140_803F: Rate limiting semântico
    SemanticNoveltyExceeded   = 0x2140_8030,
    RepetitivePayloadPattern  = 0x2140_8031,

    // 0x2140_80F0–0x2140_80FF: Genéricos
    Unknown                   = 0x2140_80F0,
}

// ─────────────────────────────────────────────────────────────────────────────
// MENSAGEM CREEK (modelo do protocolo)
// ─────────────────────────────────────────────────────────────────────────────

pub struct CreekMessage {
    pub agent_id: AgentId,
    pub topic: TopicId,
    pub payload: Vec<u8>,           // Campo suspeito — aqui aplicamos análise
    pub timestamp_ms: u64,
    pub sequence_num: u64,
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. ANÁLISE DE ENTROPIA ESTRUTURAL (Shannon + Chi-Square)
// ─────────────────────────────────────────────────────────────────────────────

/// Calcula entropia de Shannon em bits/byte
/// Payload cifrado tem entropia ~7.9-7.99 (quase máxima para bytes)
/// Texto natural: ~4-6 bits/byte
/// Dados binários estruturados: ~2-4 bits/byte
pub fn shannon_entropy(payload: &[u8]) -> f32 {
    if payload.is_empty() {
        return 0.0;
    }

    let mut freq = [0u32; 256];
    for &byte in payload.iter() {
        freq[byte as usize] += 1;
    }

    let len = payload.len() as f32;
    let mut entropy = 0.0f32;

    for count in freq.iter() {
        if *count > 0 {
            let p = *count as f32 / len;
            entropy -= p * p.log2();
        }
    }

    entropy
}

/// Teste Chi-Square para detectar distribuição não-uniforme
/// Criptografia de qualidade produz distribuição uniforme (chi-square baixo)
/// Steganografia pode introduzir padrões sutis
pub fn chi_square_uniformity(payload: &[u8]) -> f32 {
    if payload.is_empty() {
        return 0.0;
    }

    let mut freq = [0u32; 256];
    for &byte in payload.iter() {
        freq[byte as usize] += 1;
    }

    let expected = payload.len() as f32 / 256.0;
    let mut chi_sq = 0.0f32;

    for count in freq.iter() {
        let diff = *count as f32 - expected;
        chi_sq += (diff * diff) / expected;
    }

    chi_sq
}

/// Veredicto de entropia — classifica payload como limpo, suspeito ou cifrado
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EntropyVerdict {
    Clean,       // Entropia natural — texto, JSON, etc.
    Structured,  // Entropia baixa — dados binários, padding
    Suspicious,  // Entropia no limiar — possível steganografia
    Encrypted,   // Entropia máxima — criptografia forte detectada
}

pub fn analyze_entropy(payload: &[u8]) -> (EntropyVerdict, f32, f32) {
    let entropy = shannon_entropy(payload);
    let chi_sq = chi_square_uniformity(payload);

    let verdict = if entropy > COVERT_CHANNEL_ENTROPY_CEIL {
        EntropyVerdict::Encrypted
    } else if entropy > COVERT_CHANNEL_ENTROPY_FLOOR {
        EntropyVerdict::Suspicious
    } else if entropy < 2.0 {
        EntropyVerdict::Structured
    } else {
        EntropyVerdict::Clean
    };

    (verdict, entropy, chi_sq)
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. WATERMARKING TEMPORAL — Canary Tokens
// ─────────────────────────────────────────────────────────────────────────────

/// Estado de um canary token injetado no pipeline
pub struct CanaryToken {
    pub id: [u8; 16],           // ID único do canary
    pub injected_at_ms: u64,
    pub topic: TopicId,
    pub expected_digest: [u8; 32], // Hash do payload canary
}

/// Registry de canaries ativos — detecta exfiltração se canary reaparecer
pub struct CanaryRegistry {
    active: BTreeMap<[u8; 16], CanaryToken>,
    detected_count: u64,
}

impl CanaryRegistry {
    pub fn new() -> Self {
        Self {
            active: BTreeMap::new(),
            detected_count: 0,
        }
    }

    /// Injeta canary no pipeline — payload aparentemente inocente
    /// mas com marca d'água criptográfica detectável
    pub fn inject_canary(
        &mut self,
        topic: TopicId,
        now_ms: u64,
    ) -> Vec<u8> {
        let id = self.generate_canary_id(now_ms);

        // STUB: Em produção, gera payload com marca d'água esteganográfica
        // HONESTY.md: "Stub de canary. Não claima segurança criptográfica."
        let payload = self.generate_canary_payload(&id);
        let expected_digest = self.hash_payload(&payload);

        self.active.insert(id, CanaryToken {
            id,
            injected_at_ms: now_ms,
            topic,
            expected_digest,
        });

        payload
    }

    /// Verifica se payload contém canary exfiltrado
    pub fn detect_exfiltration(&mut self, payload: &[u8]) -> Option<&CanaryToken> {
        let digest = self.hash_payload(payload);

        for (_, canary) in self.active.iter() {
            // STUB: Em produção, compara marca d'água, não hash completo
            // HONESTY.md: "Stub de detecção. Comparação simplificada."
            if digest == canary.expected_digest {
                self.detected_count += 1;
                return Some(canary);
            }
        }

        None
    }

    fn generate_canary_id(&self, now_ms: u64) -> [u8; 16] {
        // STUB: ID determinístico para reproducibilidade em testes
        let mut id = [0u8; 16];
        let bytes = now_ms.to_le_bytes();
        id[0..8].copy_from_slice(&bytes);
        id
    }

    fn generate_canary_payload(&self, id: &[u8; 16]) -> Vec<u8> {
        // STUB: Payload que parece legítimo mas contém marca d'água
        let mut payload = Vec::with_capacity(256);
        payload.extend_from_slice(b"CANARY_");
        payload.extend_from_slice(id);
        payload.extend_from_slice(&[0u8; 233]); // Padding para tamanho fixo
        payload
    }

    fn hash_payload(&self, payload: &[u8]) -> [u8; 32] {
        // STUB: SHA3-256 ou fallback honesto
        // HONESTY.md: "Stub de hash. Em produção: sha3 crate ou TEE hash."
        let mut hash = [0u8; 32];
        for (i, &byte) in payload.iter().enumerate() {
            hash[i % 32] ^= byte;
        }
        hash
    }

    pub fn detected_count(&self) -> u64 {
        self.detected_count
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. DEDUPLICAÇÃO CEGA — Near-Duplicate Detection
// ─────────────────────────────────────────────────────────────────────────────

/// Fingerprint de payload para deduplicação — sensível a pequenas mudanças
/// (steganografia frequentemente altera apenas alguns bits)
pub struct BlindFingerprint {
    pub simhash: u64,           // SimHash local sensível
    pub minhash: [u64; 4],      // MinHash para similaridade aproximada
    pub size_class: u8,         // Classe de tamanho (log2 do tamanho)
}

/// Registry de fingerprints — detecta re-publicação com modificação sutil
pub struct FingerprintRegistry {
    fingerprints: BTreeMap<TopicId, Vec<BlindFingerprint>>,
    duplicate_threshold: u32,
}

impl FingerprintRegistry {
    pub fn new(threshold: u32) -> Self {
        Self {
            fingerprints: BTreeMap::new(),
            duplicate_threshold: threshold,
        }
    }

    /// Computa fingerprint cego de payload
    pub fn compute_fingerprint(payload: &[u8]) -> BlindFingerprint {
        // SimHash simplificado — XOR de chunks
        let mut simhash = 0u64;
        for chunk in payload.chunks(8) {
            let mut chunk_val = 0u64;
            for (i, &byte) in chunk.iter().enumerate() {
                chunk_val |= (byte as u64) << (i * 8);
            }
            simhash ^= chunk_val;
        }

        // MinHash stub — 4 valores de hash simplificados
        let mut minhash = [0u64; 4];
        for (i, val) in minhash.iter_mut().enumerate() {
            *val = Self::simple_hash(payload, i as u8);
        }

        let size_class = (payload.len() as f32).log2() as u8;

        BlindFingerprint { simhash, minhash, size_class }
    }

    /// Verifica se payload é near-duplicate de um anterior
    pub fn check_near_duplicate(
        &mut self,
        topic: TopicId,
        fingerprint: &BlindFingerprint,
    ) -> (bool, u32) {
        let entry = self.fingerprints.entry(topic).or_insert_with(Vec::new);

        let mut similar_count = 0u32;
        for existing in entry.iter() {
            if Self::similarity(fingerprint, existing) > 0.95 {
                similar_count += 1;
            }
        }

        let is_duplicate = similar_count >= self.duplicate_threshold;

        if !is_duplicate {
            entry.push(fingerprint.clone());
        }

        (is_duplicate, similar_count)
    }

    fn simple_hash(payload: &[u8], seed: u8) -> u64 {
        let mut hash = 0xcbf29ce484222325u64; // FNV offset basis
        for &byte in payload.iter() {
            hash ^= (byte ^ seed) as u64;
            hash = hash.wrapping_mul(0x100000001b3); // FNV prime
        }
        hash
    }

    fn similarity(a: &BlindFingerprint, b: &BlindFingerprint) -> f32 {
        if a.size_class != b.size_class {
            return 0.0;
        }

        // SimHash similarity — Hamming distance
        let sim_bits = (a.simhash ^ b.simhash).count_ones();
        let sim_sim = 1.0 - (sim_bits as f32 / 64.0);

        // MinHash similarity — Jaccard aproximado
        let mut min_matches = 0u32;
        for i in 0..4 {
            if a.minhash[i] == b.minhash[i] {
                min_matches += 1;
            }
        }
        let min_sim = min_matches as f32 / 4.0;

        (sim_sim + min_sim) / 2.0
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. RATE LIMITING SEMÂNTICO — Por Novidade, Não Volume
// ─────────────────────────────────────────────────────────────────────────────

/// Rate limiter que restringe por "novidade informacional", não por mensagens/segundo
/// Um agente pode enviar 1000 mensagens/segundo se todas forem genuinamente novas
/// Mas é bloqueado se re-publicar conteúdo similar > threshold
pub struct SemanticRateLimiter {
    /// AgentId → (topic, count de re-publicações similares)
    agent_violations: BTreeMap<AgentId, BTreeMap<TopicId, u32>>,
    threshold: u32,
    window_ms: u64,
}

impl SemanticRateLimiter {
    pub fn new(threshold: u32, window_ms: u64) -> Self {
        Self {
            agent_violations: BTreeMap::new(),
            threshold,
            window_ms,
        }
    }

    /// Registra publicação e verifica se viola limite de novidade
    pub fn record_publication(
        &mut self,
        agent: AgentId,
        topic: TopicId,
        is_duplicate: bool,
        now_ms: u64,
    ) -> bool {
        if !is_duplicate {
            return true; // Conteúdo novo — sempre permitido
        }

        let entry = self.agent_violations
            .entry(agent)
            .or_insert_with(BTreeMap::new);

        let count = entry.entry(topic).or_insert(0);
        *count += 1;

        *count < self.threshold
    }

    pub fn violation_count(&self, agent: AgentId, topic: TopicId) -> u32 {
        self.agent_violations
            .get(&agent)
            .and_then(|t| t.get(topic))
            .copied()
            .unwrap_or(0)
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. CORRELAÇÃO TEMPORAL — Detecta Coordenação por Timing
// ─────────────────────────────────────────────────────────────────────────────

/// Registro de timestamps por agente — detecta padrões de burst coordenado
pub struct TimingCorrelationEngine {
    /// AgentId → lista de timestamps de publicação
    agent_timestamps: BTreeMap<AgentId, Vec<u64>>,
    window_ms: u64,
    correlation_threshold: u32,
}

impl TimingCorrelationEngine {
    pub fn new(window_ms: u64, threshold: u32) -> Self {
        Self {
            agent_timestamps: BTreeMap::new(),
            window_ms,
            correlation_threshold: threshold,
        }
    }

    /// Registra timestamp de publicação
    pub fn record_timestamp(&mut self, agent: AgentId, timestamp_ms: u64) {
        let entry = self.agent_timestamps.entry(agent).or_insert_with(Vec::new);
        entry.push(timestamp_ms);

        // Mantém apenas timestamps dentro da janela
        let cutoff = timestamp_ms.saturating_sub(self.window_ms);
        entry.retain(|&t| t >= cutoff);
    }

    /// Detecta correlação temporal entre dois agentes
    /// Retorna score de correlação (0.0 = nenhuma, 1.0 = perfeita)
    pub fn detect_correlation(
        &self,
        agent_a: AgentId,
        agent_b: AgentId,
    ) -> f32 {
        let ts_a = match self.agent_timestamps.get(&agent_a) {
            Some(v) => v,
            None => return 0.0,
        };
        let ts_b = match self.agent_timestamps.get(&agent_b) {
            Some(v) => v,
            None => return 0.0,
        };

        if ts_a.is_empty() || ts_b.is_empty() {
            return 0.0;
        }

        // Conta coincidências dentro de tolerância de 100ms
        let mut matches = 0u32;
        let tolerance_ms = 100u64;

        for &ta in ts_a.iter() {
            for &tb in ts_b.iter() {
                if ta.abs_diff(tb) <= tolerance_ms {
                    matches += 1;
                    break; // Cada timestamp de A matcha no máximo 1 de B
                }
            }
        }

        let max_possible = core::cmp::min(ts_a.len(), ts_b.len()) as f32;
        if max_possible == 0.0 {
            return 0.0;
        }

        matches as f32 / max_possible
    }

    /// Detecta padrão de burst — múltiplos agentes publicando simultaneamente
    pub fn detect_burst_pattern(&self, now_ms: u64) -> Vec<(AgentId, AgentId, f32)> {
        let mut correlations = Vec::new();
        let agents: Vec<AgentId> = self.agent_timestamps.keys().copied().collect();

        for i in 0..agents.len() {
            for j in (i + 1)..agents.len() {
                let corr = self.detect_correlation(agents[i], agents[j]);
                if corr > 0.5 { // Threshold de correlação
                    correlations.push((agents[i], agents[j], corr));
                }
            }
        }

        correlations
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CREEKGUARD ORQUESTRADOR — Integra todos os módulos
// ─────────────────────────────────────────────────────────────────────────────

pub struct CreekGuard {
    entropy_analyzer: (), // Stateless
    canary_registry: CanaryRegistry,
    fingerprint_registry: FingerprintRegistry,
    semantic_limiter: SemanticRateLimiter,
    timing_engine: TimingCorrelationEngine,

    // Métricas
    messages_processed: u64,
    covert_channels_detected: u64,
    canaries_exfiltrated: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CreekGuardVerdict {
    Pass,           // Mensagem limpa — encaminhar
    Quarantine,     // Suspeita — quarentena silenciosa (ProAct)
    Block,          // Confirma covert channel — bloquear
    Honeypot,       // Redirecionar para honeypot
}

impl CreekGuard {
    pub fn new() -> Self {
        Self {
            entropy_analyzer: (),
            canary_registry: CanaryRegistry::new(),
            fingerprint_registry: FingerprintRegistry::new(SEMANTIC_NOVELTY_THRESHOLD),
            semantic_limiter: SemanticRateLimiter::new(SEMANTIC_NOVELTY_THRESHOLD, 60_000),
            timing_engine: TimingCorrelationEngine::new(TIMING_CORRELATION_WINDOW_MS, 3),
            messages_processed: 0,
            covert_channels_detected: 0,
            canaries_exfiltrated: 0,
        }
    }

    /// Pipeline completo de análise de mensagem Creek
    pub fn analyze_message(
        &mut self,
        msg: &CreekMessage,
    ) -> (CreekGuardVerdict, Vec<CreekGuardErrorCode>) {
        let mut errors = Vec::new();
        self.messages_processed += 1;

        // 1. ANÁLISE DE ENTROPIA
        let (entropy_verdict, entropy, _chi_sq) = analyze_entropy(&msg.payload);
        match entropy_verdict {
            EntropyVerdict::Encrypted => {
                errors.push(CreekGuardErrorCode::EntropySuspiciouslyHigh);
            }
            EntropyVerdict::Suspicious => {
                errors.push(CreekGuardErrorCode::EntropySuspiciouslyHigh);
            }
            _ => {}
        }

        // 2. DETECÇÃO DE CANARY EXFILTRADO
        if let Some(_canary) = self.canary_registry.detect_exfiltration(&msg.payload) {
            errors.push(CreekGuardErrorCode::WatermarkExfiltrated);
            self.canaries_exfiltrated += 1;
            self.covert_channels_detected += 1;
            return (CreekGuardVerdict::Block, errors);
        }

        // 3. DEDUPLICAÇÃO CEGA
        let fingerprint = FingerprintRegistry::compute_fingerprint(&msg.payload);
        let (is_duplicate, _similar_count) = self.fingerprint_registry
            .check_near_duplicate(msg.topic, &fingerprint);

        if is_duplicate {
            errors.push(CreekGuardErrorCode::NearDuplicateDetected);
        }

        // 4. RATE LIMITING SEMÂNTICO
        let allowed = self.semantic_limiter.record_publication(
            msg.agent_id,
            msg.topic,
            is_duplicate,
            msg.timestamp_ms,
        );

        if !allowed {
            errors.push(CreekGuardErrorCode::SemanticNoveltyExceeded);
        }

        // 5. CORRELAÇÃO TEMPORAL
        self.timing_engine.record_timestamp(msg.agent_id, msg.timestamp_ms);
        let bursts = self.timing_engine.detect_burst_pattern(msg.timestamp_ms);

        for (a, b, corr) in bursts.iter() {
            if *a == msg.agent_id || *b == msg.agent_id {
                if *corr > 0.8 {
                    errors.push(CreekGuardErrorCode::TimingCorrelationDetected);
                } else if *corr > 0.5 {
                    errors.push(CreekGuardErrorCode::BurstPatternDetected);
                }
            }
        }

        // INJEÇÃO DE CANARY (periódica)
        if self.messages_processed % CANARY_INJECTION_RATE as u64 == 0 {
            // STUB: Em produção, injetaria canary no pipeline Creek
            // HONESTY.md: "Stub de injeção. Não modifica pipeline real."
            let _canary_payload = self.canary_registry.inject_canary(msg.topic, msg.timestamp_ms);
        }

        // VEREDICTO FINAL
        let verdict = if errors.is_empty() {
            CreekGuardVerdict::Pass
        } else if errors.contains(&CreekGuardErrorCode::WatermarkExfiltrated) {
            CreekGuardVerdict::Block
        } else if errors.contains(&CreekGuardErrorCode::TimingCorrelationDetected) {
            CreekGuardVerdict::Honeypot
        } else if errors.len() >= 2 {
            CreekGuardVerdict::Quarantine
        } else {
            CreekGuardVerdict::Pass // Single error = observar, não bloquear
        };

        if verdict == CreekGuardVerdict::Block || verdict == CreekGuardVerdict::Honeypot {
            self.covert_channels_detected += 1;
        }

        (verdict, errors)
    }

    pub fn metrics(&self) -> CreekGuardMetrics {
        CreekGuardMetrics {
            messages_processed: self.messages_processed,
            covert_channels_detected: self.covert_channels_detected,
            canaries_exfiltrated: self.canaries_exfiltrated,
            canaries_active: self.canary_registry.active.len() as u64,
        }
    }
}

pub struct CreekGuardMetrics {
    pub messages_processed: u64,
    pub covert_channels_detected: u64,
    pub canaries_exfiltrated: u64,
    pub canaries_active: u64,
}

// ─────────────────────────────────────────────────────────────────────────────
// TESTES
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_entropy_clean_payload() {
        // Payload de texto natural — entropia baixa
        let payload = b"Hello world, this is a normal Creek message about agent coordination.";
        let (verdict, entropy, _) = analyze_entropy(payload);
        assert_eq!(verdict, EntropyVerdict::Clean);
        assert!(entropy < 6.0);
    }

    #[test]
    fn test_entropy_encrypted_payload() {
        // Payload cifrado — entropia máxima
        let mut payload = Vec::with_capacity(1024);
        for i in 0..1024u16 {
            payload.push((i * 7 + 13) as u8); // Sequência pseudo-aleatória
        }
        let (verdict, entropy, _) = analyze_entropy(&payload);
        assert_eq!(verdict, EntropyVerdict::Encrypted);
        assert!(entropy > 7.9);
    }

    #[test]
    fn test_canary_exfiltration() {
        let mut guard = CreekGuard::new();
        let topic: TopicId = "test-topic";

        // Injeta canary
        let canary_payload = guard.canary_registry.inject_canary(topic, 1000);

        // Detecta exfiltração
        let detected = guard.canary_registry.detect_exfiltration(&canary_payload);
        assert!(detected.is_some());
    }

    #[test]
    fn test_near_duplicate_detection() {
        let mut registry = FingerprintRegistry::new(2);
        let topic: TopicId = "test-topic";

        let payload1 = b"Agent A reports status: all systems nominal.";
        let fp1 = FingerprintRegistry::compute_fingerprint(payload1);
        let (dup1, _) = registry.check_near_duplicate(topic, &fp1);
        assert!(!dup1); // Primeira vez — não é duplicata

        let payload2 = b"Agent A reports status: all systems nominal."; // Idêntico
        let fp2 = FingerprintRegistry::compute_fingerprint(payload2);
        let (dup2, count) = registry.check_near_duplicate(topic, &fp2);
        assert!(dup2); // Segunda vez — duplicata
        assert_eq!(count, 1);
    }

    #[test]
    fn test_semantic_rate_limiter() {
        let mut limiter = SemanticRateLimiter::new(3, 60_000);
        let agent = [0u8; 32];
        let topic: TopicId = "test-topic";

        // Conteúdo novo — sempre permitido
        assert!(limiter.record_publication(agent, topic, false, 1000));
        assert!(limiter.record_publication(agent, topic, false, 2000));

        // Duplicata 1 — permitido
        assert!(limiter.record_publication(agent, topic, true, 3000));
        // Duplicata 2 — permitido
        assert!(limiter.record_publication(agent, topic, true, 4000));
        // Duplicata 3 — permitido
        assert!(limiter.record_publication(agent, topic, true, 5000));
        // Duplicata 4 — BLOQUEADO (threshold = 3)
        assert!(!limiter.record_publication(agent, topic, true, 6000));
    }

    #[test]
    fn test_timing_correlation() {
        let mut engine = TimingCorrelationEngine::new(5000, 3);
        let agent_a = [0xAAu8; 32];
        let agent_b = [0xBBu8; 32];

        // Agent A publica em t=1000, 2000, 3000
        engine.record_timestamp(agent_a, 1000);
        engine.record_timestamp(agent_a, 2000);
        engine.record_timestamp(agent_a, 3000);

        // Agent B publica em t=1050, 2050, 3050 (correlacionado ~50ms offset)
        engine.record_timestamp(agent_b, 1050);
        engine.record_timestamp(agent_b, 2050);
        engine.record_timestamp(agent_b, 3050);

        let corr = engine.detect_correlation(agent_a, agent_b);
        assert!(corr > 0.8); // Alta correlação detectada
    }

    #[test]
    fn test_creekguard_pipeline() {
        let mut guard = CreekGuard::new();
        let agent = [0xCCu8; 32];
        let topic: TopicId = "agents.status";

        // Mensagem limpa
        let msg = CreekMessage {
            agent_id: agent,
            topic,
            payload: b"Status: normal, load: 45%, memory: 60%".to_vec(),
            timestamp_ms: 1000,
            sequence_num: 1,
        };
        let (verdict, errors) = guard.analyze_message(&msg);
        assert_eq!(verdict, CreekGuardVerdict::Pass);
        assert!(errors.is_empty());

        // Mensagem cifrada (covert channel simulado)
        let encrypted_payload: Vec<u8> = (0..512).map(|i| (i * 17 + 31) as u8).collect();
        let msg2 = CreekMessage {
            agent_id: agent,
            topic,
            payload: encrypted_payload,
            timestamp_ms: 2000,
            sequence_num: 2,
        };
        let (verdict2, errors2) = guard.analyze_message(&msg2);
        assert!(errors2.contains(&CreekGuardErrorCode::EntropySuspiciouslyHigh));
    }

    #[test]
    fn test_error_code_namespace() {
        assert_eq!(CreekGuardErrorCode::EntropySuspiciouslyHigh as u32, 0x2140_8001);
        assert_eq!(CreekGuardErrorCode::TimingCorrelationDetected as u32, 0x2140_8010);
        assert_eq!(CreekGuardErrorCode::WatermarkExfiltrated as u32, 0x2140_8021);
        assert_eq!(CreekGuardErrorCode::SemanticNoveltyExceeded as u32, 0x2140_8030);
    }
}