// crates/memory-system/src/store.rs
//! Banco vetorial com selagem Merkle externa
//!
//! API qdrant-client 1.18 verificada:
//! - Qdrant::from_url(url).build()
//! - CreateCollectionBuilder::new(name).vectors_config(VectorParamsBuilder::new(dim, Distance::Cosine))
//! - UpsertPointsBuilder::new(collection, points)
//! - QueryPointsBuilder::new(collection).query(vector).limit(k).with_payload(true)
//! - PointStruct::new(id, vector, payload)

use qdrant_client::Qdrant;
use qdrant_client::qdrant::{
    CreateCollectionBuilder, VectorParamsBuilder, Distance,
    UpsertPointsBuilder, QueryPointsBuilder, PointStruct,
};
use rs_merkle::{MerkleTree, algorithms::Sha256 as MerkleSha256, Hasher};
use sha2::Digest;
use std::sync::Arc;
use tokio::sync::RwLock;
use crate::error::MemoryError;
use crate::vector::{VectorEntry, SealedVector};

/// Operação no banco vetorial (serializada para Merkle leaf).
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub enum VectorOp {
    Insert { id: String, vector_hash: [u8; 32], metadata_hash: [u8; 32] },
    Delete { id: String },
}

impl VectorOp {
    pub fn leaf_hash(&self) -> [u8; 32] {
        let bytes = serde_json::to_vec(self).expect("VectorOp serializes");
        let result = sha2::Sha256::digest(&bytes);
        let mut hash = [0u8; 32];
        hash.copy_from_slice(&result);
        hash
    }
}

/// Banco vetorial com selagem Merkle externa.
pub struct MerkleSealedVectorStore {
    qdrant: Qdrant,
    collection_name: String,
    dimension: u64,
    merkle: Arc<RwLock<MerkleTree<MerkleSha256>>>,
    op_log: Arc<RwLock<Vec<VectorOp>>>,
}

impl MerkleSealedVectorStore {
    pub async fn new(
        qdrant_url: &str,
        collection_name: &str,
        dimension: u64,
    ) -> Result<Self, MemoryError> {
        let qdrant = Qdrant::from_url(qdrant_url)
            .build()
            .map_err(|e| MemoryError::Connection(e.to_string()))?;

        // Verificar se coleção existe, criar se não
        let collections = qdrant.list_collections().await?;
        let exists = collections.collections.iter().any(|c| c.name == collection_name);

        if !exists {
            qdrant.create_collection(
                CreateCollectionBuilder::new(collection_name)
                    .vectors_config(VectorParamsBuilder::new(dimension, Distance::Cosine))
            ).await?;
        }

        Ok(Self {
            qdrant,
            collection_name: collection_name.to_string(),
            dimension,
            merkle: Arc::new(RwLock::new(MerkleTree::new())),
            op_log: Arc::new(RwLock::new(Vec::new())),
        })
    }

    /// Insere ponto com selagem Merkle.
    pub async fn insert(&self, entry: VectorEntry) -> Result<usize, MemoryError> {
        // Validar dimensão
        if entry.vector.len() as u64 != self.dimension {
            return Err(MemoryError::InvalidDimension {
                expected: self.dimension,
                got: entry.vector.len(),
            });
        }

        // Criar vetor selado
        let sealed = SealedVector::new(entry);

        // Criar operação para Merkle
        let metadata_hash = {
            let mut hasher = sha2::Sha256::new();
            if let Ok(bytes) = serde_json::to_vec(&sealed.entry.metadata) {
                hasher.update(&bytes);
            }
            let result = hasher.finalize();
            let mut hash = [0u8; 32];
            hash.copy_from_slice(&result);
            hash
        };

        let op = VectorOp::Insert {
            id: sealed.entry.id.clone(),
            vector_hash: sealed.leaf_hash,
            metadata_hash,
        };
        let leaf_hash = op.leaf_hash();

        // Inserir no Qdrant usando API 1.18 builder pattern
        let point = PointStruct::new(
            sealed.entry.id.clone(),
            sealed.entry.vector.clone(),
            [
                ("metadata", sealed.entry.metadata.clone().into()),
                ("leaf_hash", hex::encode(sealed.leaf_hash).into()),
                ("nonce", hex::encode(sealed.nonce).into()),
                ("timestamp", sealed.entry.timestamp.into()),
            ],
        );

        self.qdrant.upsert_points(
            UpsertPointsBuilder::new(&self.collection_name, vec![point])
        ).await?;

        // Atualizar Merkle Tree
        let mut merkle = self.merkle.write().await;
        let mut op_log = self.op_log.write().await;

        merkle.insert(leaf_hash);
        merkle.commit();
        op_log.push(op);

        Ok(op_log.len() - 1)
    }

    /// Busca vetorial com prova de inclusão opcional.
    pub async fn search(
        &self,
        query: Vec<f32>,
        top_k: usize,
        with_proof: bool,
    ) -> Result<Vec<SearchResult>, MemoryError> {
        if query.len() as u64 != self.dimension {
            return Err(MemoryError::InvalidDimension {
                expected: self.dimension,
                got: query.len(),
            });
        }

        let search_result = self.qdrant.query(
            QueryPointsBuilder::new(&self.collection_name)
                .query(query)
                .limit(top_k as u64)
                .with_payload(true)
        ).await?;

        let merkle = self.merkle.read().await;
        let op_log = self.op_log.read().await;

        let results: Vec<SearchResult> = search_result.result.into_iter()
            .map(|scored_point| {
                let id = scored_point.id.map(|id| id.point_id_options.map(|o| match o { qdrant_client::qdrant::point_id::PointIdOptions::Num(n) => n.to_string(), qdrant_client::qdrant::point_id::PointIdOptions::Uuid(u) => u }).unwrap_or_default()).unwrap_or_default();

                let payload: serde_json::Map<String, serde_json::Value> = scored_point.payload
                    .into_iter()
                    .map(|(k, v)| (k, serde_json::Value::try_from(v).unwrap_or(serde_json::Value::Null)))
                    .collect();

                let inclusion_proof = if with_proof {
                    // Encontrar índice no op_log
                    op_log.iter().position(|op| match op {
                        VectorOp::Insert { id: op_id, .. } => op_id == &id,
                        _ => false,
                    }).and_then(|idx| {
                        let leaf_hash = op_log[idx].leaf_hash();
                        let indices = vec![idx];
                        let proof = merkle.proof(&indices);
                        let root = merkle.root()?;
                        Some(InclusionProof {
                            leaf_index: idx,
                            leaf_hash,
                            proof_bytes: proof.to_bytes(),
                            root_hash: root,
                        })
                    })
                } else {
                    None
                };

                SearchResult {
                    id,
                    score: scored_point.score,
                    payload: serde_json::Value::Object(payload),
                    inclusion_proof,
                }
            })
            .collect();

        Ok(results)
    }

    /// Retorna root hash atual da Merkle Tree.
    pub async fn merkle_root(&self) -> Option<[u8; 32]> {
        let merkle = self.merkle.read().await;
        merkle.root()
    }

    /// Retorna tamanho atual da árvore.
    pub async fn tree_size(&self) -> usize {
        let op_log = self.op_log.read().await;
        op_log.len()
    }
}

/// Resultado de busca com prova de inclusão.
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub id: String,
    pub score: f32,
    pub payload: serde_json::Value,
    pub inclusion_proof: Option<InclusionProof>,
}

/// Prova de inclusão Merkle.
#[derive(Debug, Clone)]
pub struct InclusionProof {
    pub leaf_index: usize,
    pub leaf_hash: [u8; 32],
    pub proof_bytes: Vec<u8>,
    pub root_hash: [u8; 32],
}

impl InclusionProof {
    /// Verifica a prova de inclusão offline.
    pub fn verify(&self) -> Result<bool, MemoryError> {
        let merkle_proof = rs_merkle::MerkleProof::<MerkleSha256>::try_from(
            self.proof_bytes.as_slice()
        ).map_err(|e| MemoryError::Merkle(e.to_string()))?;

        let indices = vec![self.leaf_index];
        let leaves = vec![self.leaf_hash];

        Ok(merkle_proof.verify(
            self.root_hash,
            &indices,
            &leaves,
            self.leaf_index + 1,
        ))
    }
}
