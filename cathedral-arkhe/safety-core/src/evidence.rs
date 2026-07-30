//! O termo "Witness" foi rebaixado. Isto é "RetrievalAnchor" (Metadados de recuperação).

/// Metadados de recuperação do RAG. NÃO é uma prova formal no sentido Lean.
#[derive(Debug, Clone)]
pub struct RetrievalAnchor {
    pub source_node_id: usize,
    pub semantic_similarity: f64,
    pub anchor_hash: u64, // Hash para rastreamento, não prova lógica
}
