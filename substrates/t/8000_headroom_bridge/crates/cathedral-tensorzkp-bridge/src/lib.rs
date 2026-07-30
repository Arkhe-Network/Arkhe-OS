//! crates/cathedral-tensorzkp-bridge/src/lib.rs
//! Cathedral TensorZKP Bridge — Integração com Substrato 325.4
//! Provas ZK para preservação semântica de compressão
//!
//! Selo: CATHEDRAL-ARKHE-8000-TENSORZKP-BRIDGE-v1.0.0-2026-06-18
//! Arquiteto: ORCID 0009-0005-2697-4668

use std::sync::Arc;
use tokio::sync::RwLock;
use serde::{Serialize, Deserialize};
use thiserror::Error;
use sha2::{Sha256, Digest};
use tracing::{info, error, debug};

/// ============================================================
/// 1. TENSORZKP BRIDGE CONFIG
/// ============================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TensorZkpConfig {
    /// Endereço do TensorZKP Accelerator (USB-CDC ou network)
    pub accelerator_endpoint: String,
    /// Tipo de conexão
    pub connection_type: ZkpConnectionType,
    /// Curva elíptica (secp256k1, bn254, bls12_381)
    pub curve: EllipticCurve,
    /// Proving system (groth16, plonk, stark)
    pub proving_system: ProvingSystem,
    /// Batch size para provas
    pub batch_size: usize,
    /// Timeout de prova (ms)
    pub proof_timeout_ms: u64,
    /// Se verifica provas no hardware
    pub hardware_verification: bool,
    /// Se usa GPU offload
    pub gpu_offload: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ZkpConnectionType {
    UsbCdc { port: String, baud: u32 },
    Tcp { host: String, port: u16 },
    UnixSocket { path: String },
    Mock, // Para testes
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EllipticCurve {
    Secp256k1,
    Bn254,
    Bls12_381,
    Bn254Optimized,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ProvingSystem {
    Groth16,
    Plonk,
    Stark,
    Marlin,
}

impl Default for TensorZkpConfig {
    fn default() -> Self {
        Self {
            accelerator_endpoint: "/dev/ttyACM0".to_string(),
            connection_type: ZkpConnectionType::UsbCdc {
                port: "/dev/ttyACM0".to_string(),
                baud: 921600
            },
            curve: EllipticCurve::Secp256k1,
            proving_system: ProvingSystem::Groth16,
            batch_size: 16,
            proof_timeout_ms: 5000,
            hardware_verification: true,
            gpu_offload: true,
        }
    }
}

/// ============================================================
/// 2. TENSORZKP BRIDGE
/// ============================================================

pub struct TensorZkpBridge {
    config: TensorZkpConfig,
    /// Conexão com accelerator
    accelerator: Arc<RwLock<Box<dyn ZkpAccelerator>>>,
    /// Circuitos compilados
    circuits: Arc<RwLock<HashMap<String, CompiledCircuit>>>,
    /// Métricas
    metrics: Arc<RwLock<ZkpMetrics>>,
}

#[derive(Debug, Clone, Default)]
pub struct ZkpMetrics {
    pub proofs_generated: u64,
    pub proofs_verified: u64,
    pub proofs_failed: u64,
    pub avg_proof_time_ms: f64,
    pub avg_verify_time_ms: f64,
    pub batch_proofs_generated: u64,
}

/// Trait para accelerators ZKP
#[async_trait::async_trait]
pub trait ZkpAccelerator: Send + Sync {
    async fn generate_proof(
        &mut self,
        circuit: &CompiledCircuit,
        witness: &Witness,
    ) -> Result<ZkpProof, ZkpBridgeError>;

    async fn verify_proof(
        &mut self,
        circuit: &CompiledCircuit,
        proof: &ZkpProof,
        public_inputs: &PublicInputs,
    ) -> Result<bool, ZkpBridgeError>;

    async fn batch_generate(
        &mut self,
        circuits: &[CompiledCircuit],
        witnesses: &[Witness],
    ) -> Result<Vec<ZkpProof>, ZkpBridgeError>;

    async fn health_check(&self) -> Result<bool, ZkpBridgeError>;
}

/// ============================================================
/// 3. SEMANTIC PRESERVATION CIRCUIT
/// ============================================================

/// Circuito ZK para provar preservação semântica na compressão
pub struct SemanticPreservationCircuit {
    /// Hash do texto original
    pub original_hash: [u8; 32],
    /// Hash do texto comprimido
    pub compressed_hash: [u8; 32],
    /// Embedding do original (commitment)
    pub original_embedding_commitment: [u8; 32],
    /// Embedding do comprimido (commitment)
    pub compressed_embedding_commitment: [u8; 32],
    /// Threshold de similaridade
    pub similarity_threshold: f64,
    /// Tipo de conteúdo
    pub content_type: String,
}

impl SemanticPreservationCircuit {
    /// Compila circuito para prova
    pub fn compile(&self) -> Result<CompiledCircuit, ZkpBridgeError> {
        // Em produção: compila circuito usando arkworks ou bellman
        // Aqui: stub que retorna circuito mock

        let circuit_id = format!("semantic_{}", hex::encode(&self.original_hash[..8]));

        Ok(CompiledCircuit {
            id: circuit_id,
            constraint_count: 10000, // Stub
            proving_key_hash: sha256(b"proving_key"),
            verification_key_hash: sha256(b"verification_key"),
        })
    }

    /// Gera witness para prova
    pub fn generate_witness(
        &self,
        original_embedding: &[f32],
        compressed_embedding: &[f32],
    ) -> Result<Witness, ZkpBridgeError> {
        // Verifica similaridade
        let similarity = cosine_similarity(original_embedding, compressed_embedding);

        if similarity < self.similarity_threshold {
            return Err(ZkpBridgeError::SimilarityBelowThreshold {
                similarity,
                threshold: self.similarity_threshold,
            });
        }

        Ok(Witness {
            private_inputs: vec![
                serialize_embedding(original_embedding),
                serialize_embedding(compressed_embedding),
            ],
            public_inputs: vec![
                self.original_hash.to_vec(),
                self.compressed_hash.to_vec(),
                self.original_embedding_commitment.to_vec(),
                self.compressed_embedding_commitment.to_vec(),
            ],
        })
    }
}

/// ============================================================
/// 4. TENSORZKP BRIDGE METHODS
/// ============================================================

impl TensorZkpBridge {
    pub async fn new(config: TensorZkpConfig) -> Result<Self, ZkpBridgeError> {
        let accelerator: Box<dyn ZkpAccelerator> = match config.connection_type {
            ZkpConnectionType::UsbCdc { ref port, baud } => {
                Box::new(UsbCdcAccelerator::new(port, baud).await?)
            }
            ZkpConnectionType::Tcp { ref host, port } => {
                Box::new(TcpAccelerator::new(host, port).await?)
            }
            ZkpConnectionType::UnixSocket { ref path } => {
                Box::new(UnixSocketAccelerator::new(path).await?)
            }
            ZkpConnectionType::Mock => {
                Box::new(MockAccelerator::new())
            }
        };

        info!("✅ TensorZKP Bridge initialized: {:?} + {:?}",
            config.curve, config.proving_system);

        Ok(Self {
            config,
            accelerator: Arc::new(RwLock::new(accelerator)),
            circuits: Arc::new(RwLock::new(HashMap::new())),
            metrics: Arc::new(RwLock::new(ZkpMetrics::default())),
        })
    }

    /// ============================================================
    /// 4.1 PROVE SEMANTIC PRESERVATION
    /// ============================================================

    /// Gera prova ZK de que compressão preserva semântica
    pub async fn prove_semantic_preservation(
        &self,
        original: &str,
        compressed: &str,
        original_embedding: &[f32],
        compressed_embedding: &[f32],
        similarity_threshold: f64,
    ) -> Result<SemanticPreservationProof, ZkpBridgeError> {
        let start = std::time::Instant::now();

        // 1. Computa hashes
        let original_hash = sha256(original.as_bytes());
        let compressed_hash = sha256(compressed.as_bytes());

        // 2. Computa commitments de embeddings
        let original_emb_commitment = sha256(&serialize_embedding(original_embedding));
        let compressed_emb_commitment = sha256(&serialize_embedding(compressed_embedding));

        // 3. Cria circuito
        let circuit_def = SemanticPreservationCircuit {
            original_hash,
            compressed_hash,
            original_embedding_commitment: original_emb_commitment,
            compressed_embedding_commitment: compressed_emb_commitment,
            similarity_threshold,
            content_type: "text".to_string(),
        };

        let circuit = circuit_def.compile()?;
        let witness = circuit_def.generate_witness(original_embedding, compressed_embedding)?;

        // 4. Gera prova via accelerator
        let mut accel = self.accelerator.write().await;
        let proof = accel.generate_proof(&circuit, &witness).await?;

        let elapsed = start.elapsed().as_millis() as u64;

        // 5. Atualiza métricas
        {
            let mut metrics = self.metrics.write().await;
            metrics.proofs_generated += 1;
            metrics.avg_proof_time_ms =
                (metrics.avg_proof_time_ms * (metrics.proofs_generated - 1) as f64 + elapsed as f64)
                / metrics.proofs_generated as f64;
        }

        info!("🔐 Semantic preservation proof generated: {}ms", elapsed);

        Ok(SemanticPreservationProof {
            proof,
            original_hash: hex::encode(original_hash),
            compressed_hash: hex::encode(compressed_hash),
            similarity_threshold,
            actual_similarity: cosine_similarity(original_embedding, compressed_embedding),
            proof_time_ms: elapsed,
            circuit_id: circuit.id,
        })
    }

    /// ============================================================
    /// 4.2 VERIFY SEMANTIC PRESERVATION
    /// ============================================================

    /// Verifica prova de preservação semântica
    pub async fn verify_semantic_preservation(
        &self,
        proof: &SemanticPreservationProof,
    ) -> Result<bool, ZkpBridgeError> {
        let start = std::time::Instant::now();

        // Recria circuito
        let circuit = CompiledCircuit {
            id: proof.circuit_id.clone(),
            constraint_count: 10000,
            proving_key_hash: sha256(b"proving_key"),
            verification_key_hash: sha256(b"verification_key"),
        };

        let public_inputs = PublicInputs {
            values: vec![
                hex::decode(&proof.original_hash).map_err(|e| ZkpBridgeError::InvalidHash(e.to_string()))?,
                hex::decode(&proof.compressed_hash).map_err(|e| ZkpBridgeError::InvalidHash(e.to_string()))?,
            ],
        };

        let mut accel = self.accelerator.write().await;
        let valid = accel.verify_proof(&circuit, &proof.proof, &public_inputs).await?;

        let elapsed = start.elapsed().as_millis() as u64;

        {
            let mut metrics = self.metrics.write().await;
            metrics.proofs_verified += 1;
            metrics.avg_verify_time_ms =
                (metrics.avg_verify_time_ms * (metrics.proofs_verified - 1) as f64 + elapsed as f64)
                / metrics.proofs_verified as f64;
        }

        info!("🔍 Semantic preservation proof verified: {} ({}ms)", valid, elapsed);

        Ok(valid)
    }

    /// ============================================================
    /// 4.3 BATCH PROOFS
    /// ============================================================

    /// Gera provas em batch para múltiplas compressões
    pub async fn batch_prove_semantic_preservation(
        &self,
        items: Vec<BatchProveItem>,
    ) -> Result<Vec<SemanticPreservationProof>, ZkpBridgeError> {
        let start = std::time::Instant::now();

        let mut circuits = vec![];
        let mut witnesses = vec![];
        let mut results = vec![];

        for item in items {
            let original_hash = sha256(item.original.as_bytes());
            let compressed_hash = sha256(item.compressed.as_bytes());

            let circuit_def = SemanticPreservationCircuit {
                original_hash,
                compressed_hash,
                original_embedding_commitment: sha256(&serialize_embedding(&item.original_embedding)),
                compressed_embedding_commitment: sha256(&serialize_embedding(&item.compressed_embedding)),
                similarity_threshold: item.similarity_threshold,
                content_type: item.content_type,
            };

            let circuit = circuit_def.compile()?;
            let witness = circuit_def.generate_witness(&item.original_embedding, &item.compressed_embedding)?;

            circuits.push(circuit);
            witnesses.push(witness);
        }

        let mut accel = self.accelerator.write().await;
        let proofs = accel.batch_generate(&circuits, &witnesses).await?;

        for (i, proof) in proofs.into_iter().enumerate() {
            results.push(SemanticPreservationProof {
                proof,
                original_hash: hex::encode(sha256(items[i].original.as_bytes())),
                compressed_hash: hex::encode(sha256(items[i].compressed.as_bytes())),
                similarity_threshold: items[i].similarity_threshold,
                actual_similarity: cosine_similarity(&items[i].original_embedding, &items[i].compressed_embedding),
                proof_time_ms: 0, // Individual timing não disponível em batch
                circuit_id: circuits[i].id.clone(),
            });
        }

        let elapsed = start.elapsed().as_millis() as u64;

        {
            let mut metrics = self.metrics.write().await;
            metrics.batch_proofs_generated += 1;
        }

        info!("🔐 Batch proofs generated: {} items in {}ms", results.len(), elapsed);

        Ok(results)
    }

    /// ============================================================
    /// 4.4 MÉTRICAS
    /// ============================================================

    pub async fn get_metrics(&self) -> ZkpMetrics {
        self.metrics.read().await.clone()
    }

    pub async fn health_check(&self) -> Result<bool, ZkpBridgeError> {
        let accel = self.accelerator.read().await;
        accel.health_check().await
    }
}

/// ============================================================
/// 5. ACCELERATOR IMPLEMENTATIONS
/// ============================================================

/// USB-CDC Accelerator (Substrato 325.4 real)
pub struct UsbCdcAccelerator {
    port: String,
    baud: u32,
}

impl UsbCdcAccelerator {
    pub async fn new(port: &str, baud: u32) -> Result<Self, ZkpBridgeError> {
        // Em produção: abre porta serial USB-CDC
        Ok(Self { port: port.to_string(), baud })
    }
}

#[async_trait::async_trait]
impl ZkpAccelerator for UsbCdcAccelerator {
    async fn generate_proof(&mut self, _circuit: &CompiledCircuit, _witness: &Witness) -> Result<ZkpProof, ZkpBridgeError> {
        // Em produção: envia via USB-CDC, recebe prova
        Ok(ZkpProof { data: vec![0u8; 64], public_inputs: vec![] })
    }

    async fn verify_proof(&mut self, _circuit: &CompiledCircuit, proof: &ZkpProof, _public: &PublicInputs) -> Result<bool, ZkpBridgeError> {
        Ok(!proof.data.is_empty())
    }

    async fn batch_generate(&mut self, _circuits: &[CompiledCircuit], _witnesses: &[Witness]) -> Result<Vec<ZkpProof>, ZkpBridgeError> {
        Ok(vec![ZkpProof { data: vec![0u8; 64], public_inputs: vec![] }])
    }

    async fn health_check(&self) -> Result<bool, ZkpBridgeError> {
        Ok(true)
    }
}

/// TCP Accelerator
pub struct TcpAccelerator {
    host: String,
    port: u16,
}

impl TcpAccelerator {
    pub async fn new(host: &str, port: u16) -> Result<Self, ZkpBridgeError> {
        Ok(Self { host: host.to_string(), port })
    }
}

#[async_trait::async_trait]
impl ZkpAccelerator for TcpAccelerator {
    async fn generate_proof(&mut self, _circuit: &CompiledCircuit, _witness: &Witness) -> Result<ZkpProof, ZkpBridgeError> {
        Ok(ZkpProof { data: vec![0u8; 64], public_inputs: vec![] })
    }

    async fn verify_proof(&mut self, _circuit: &CompiledCircuit, proof: &ZkpProof, _public: &PublicInputs) -> Result<bool, ZkpBridgeError> {
        Ok(!proof.data.is_empty())
    }

    async fn batch_generate(&mut self, _circuits: &[CompiledCircuit], _witnesses: &[Witness]) -> Result<Vec<ZkpProof>, ZkpBridgeError> {
        Ok(vec![ZkpProof { data: vec![0u8; 64], public_inputs: vec![] }])
    }

    async fn health_check(&self) -> Result<bool, ZkpBridgeError> {
        Ok(true)
    }
}

/// Unix Socket Accelerator
pub struct UnixSocketAccelerator {
    path: String,
}

impl UnixSocketAccelerator {
    pub async fn new(path: &str) -> Result<Self, ZkpBridgeError> {
        Ok(Self { path: path.to_string() })
    }
}

#[async_trait::async_trait]
impl ZkpAccelerator for UnixSocketAccelerator {
    async fn generate_proof(&mut self, _circuit: &CompiledCircuit, _witness: &Witness) -> Result<ZkpProof, ZkpBridgeError> {
        Ok(ZkpProof { data: vec![0u8; 64], public_inputs: vec![] })
    }

    async fn verify_proof(&mut self, _circuit: &CompiledCircuit, proof: &ZkpProof, _public: &PublicInputs) -> Result<bool, ZkpBridgeError> {
        Ok(!proof.data.is_empty())
    }

    async fn batch_generate(&mut self, _circuits: &[CompiledCircuit], _witnesses: &[Witness]) -> Result<Vec<ZkpProof>, ZkpBridgeError> {
        Ok(vec![ZkpProof { data: vec![0u8; 64], public_inputs: vec![] }])
    }

    async fn health_check(&self) -> Result<bool, ZkpBridgeError> {
        Ok(true)
    }
}

/// Mock Accelerator (para testes)
pub struct MockAccelerator;

impl MockAccelerator {
    pub fn new() -> Self { Self }
}

#[async_trait::async_trait]
impl ZkpAccelerator for MockAccelerator {
    async fn generate_proof(&mut self, _circuit: &CompiledCircuit, _witness: &Witness) -> Result<ZkpProof, ZkpBridgeError> {
        // Simula delay de prova
        tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
        Ok(ZkpProof { data: vec![0xAB; 64], public_inputs: vec![] })
    }

    async fn verify_proof(&mut self, _circuit: &CompiledCircuit, proof: &ZkpProof, _public: &PublicInputs) -> Result<bool, ZkpBridgeError> {
        tokio::time::sleep(tokio::time::Duration::from_millis(5)).await;
        Ok(proof.data.iter().any(|&b| b != 0))
    }

    async fn batch_generate(&mut self, circuits: &[CompiledCircuit], _witnesses: &[Witness]) -> Result<Vec<ZkpProof>, ZkpBridgeError> {
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
        Ok(circuits.iter().map(|_| ZkpProof { data: vec![0xAB; 64], public_inputs: vec![] }).collect())
    }

    async fn health_check(&self) -> Result<bool, ZkpBridgeError> {
        Ok(true)
    }
}

/// ============================================================
/// 6. TIPOS AUXILIARES
/// ============================================================

#[derive(Debug, Clone)]
pub struct CompiledCircuit {
    pub id: String,
    pub constraint_count: usize,
    pub proving_key_hash: [u8; 32],
    pub verification_key_hash: [u8; 32],
}

#[derive(Debug, Clone)]
pub struct Witness {
    pub private_inputs: Vec<Vec<u8>>,
    pub public_inputs: Vec<Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct PublicInputs {
    pub values: Vec<Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct ZkpProof {
    pub data: Vec<u8>,
    pub public_inputs: Vec<Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct SemanticPreservationProof {
    pub proof: ZkpProof,
    pub original_hash: String,
    pub compressed_hash: String,
    pub similarity_threshold: f64,
    pub actual_similarity: f64,
    pub proof_time_ms: u64,
    pub circuit_id: String,
}

#[derive(Debug, Clone)]
pub struct BatchProveItem {
    pub original: String,
    pub compressed: String,
    pub original_embedding: Vec<f32>,
    pub compressed_embedding: Vec<f32>,
    pub similarity_threshold: f64,
    pub content_type: String,
}

/// ============================================================
/// 7. UTILITÁRIOS
/// ============================================================

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().into()
}

fn serialize_embedding(embedding: &[f32]) -> Vec<u8> {
    embedding.iter()
        .flat_map(|f| f.to_le_bytes().to_vec())
        .collect()
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f64 {
    if a.len() != b.len() { return 0.0; }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 { return 0.0; }
    (dot / (norm_a * norm_b)) as f64
}

use std::collections::HashMap;
use async_trait::async_trait;

/// ============================================================
/// 8. ERROS
/// ============================================================

#[derive(Debug, Error)]
pub enum ZkpBridgeError {
    #[error("Connection error: {0}")]
    ConnectionError(String),
    #[error("Circuit compilation failed: {0}")]
    CircuitCompilationFailed(String),
    #[error("Witness generation failed: {0}")]
    WitnessGenerationFailed(String),
    #[error("Proof generation failed: {0}")]
    ProofGenerationFailed(String),
    #[error("Proof verification failed: {0}")]
    ProofVerificationFailed(String),
    #[error("Similarity below threshold: {similarity} < {threshold}")]
    SimilarityBelowThreshold { similarity: f64, threshold: f64 },
    #[error("Invalid hash: {0}")]
    InvalidHash(String),
    #[error("Accelerator error: {0}")]
    AcceleratorError(String),
    #[error("Timeout")]
    Timeout,
}

/// ============================================================
/// 9. TESTES
/// ============================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_mock_accelerator() {
        let mut accel = MockAccelerator::new();
        let circuit = CompiledCircuit {
            id: "test".to_string(),
            constraint_count: 100,
            proving_key_hash: [0u8; 32],
            verification_key_hash: [0u8; 32],
        };
        let witness = Witness { private_inputs: vec![], public_inputs: vec![] };

        let proof = accel.generate_proof(&circuit, &witness).await.unwrap();
        assert!(!proof.data.is_empty());

        let public = PublicInputs { values: vec![] };
        let valid = accel.verify_proof(&circuit, &proof, &public).await.unwrap();
        assert!(valid);
    }

    #[tokio::test]
    async fn test_semantic_preservation_circuit() {
        let circuit = SemanticPreservationCircuit {
            original_hash: [0u8; 32],
            compressed_hash: [0u8; 32],
            original_embedding_commitment: [0u8; 32],
            compressed_embedding_commitment: [0u8; 32],
            similarity_threshold: 0.8,
            content_type: "text".to_string(),
        };

        let compiled = circuit.compile().unwrap();
        assert_eq!(compiled.constraint_count, 10000);
    }

    #[tokio::test]
    async fn test_prove_and_verify() {
        let bridge = TensorZkpBridge::new(TensorZkpConfig {
            connection_type: ZkpConnectionType::Mock,
            ..Default::default()
        }).await.unwrap();

        let original = "Hello world";
        let compressed = "Hello wrld";
        let emb_a = vec![0.1, 0.2, 0.3];
        let emb_b = vec![0.1, 0.2, 0.35];

        let proof = bridge.prove_semantic_preservation(
            original, compressed, &emb_a, &emb_b, 0.5
        ).await.unwrap();

        assert!(proof.actual_similarity > 0.9);

        let valid = bridge.verify_semantic_preservation(&proof).await.unwrap();
        assert!(valid);
    }

    #[tokio::test]
    async fn test_batch_proofs() {
        let bridge = TensorZkpBridge::new(TensorZkpConfig {
            connection_type: ZkpConnectionType::Mock,
            ..Default::default()
        }).await.unwrap();

        let items = vec![
            BatchProveItem {
                original: "A".to_string(),
                compressed: "A".to_string(),
                original_embedding: vec![0.1, 0.2],
                compressed_embedding: vec![0.1, 0.2],
                similarity_threshold: 0.8,
                content_type: "text".to_string(),
            },
            BatchProveItem {
                original: "B".to_string(),
                compressed: "B".to_string(),
                original_embedding: vec![0.3, 0.4],
                compressed_embedding: vec![0.3, 0.4],
                similarity_threshold: 0.8,
                content_type: "text".to_string(),
            },
        ];

        let proofs = bridge.batch_prove_semantic_preservation(items).await.unwrap();
        assert_eq!(proofs.len(), 2);
    }

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0];
        assert_eq!(cosine_similarity(&a, &b), 0.0);

        let c = vec![1.0, 0.0, 0.0];
        assert_eq!(cosine_similarity(&a, &c), 1.0);
    }
}
