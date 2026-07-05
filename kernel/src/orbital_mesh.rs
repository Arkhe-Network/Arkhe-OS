// ============================================================================
// ARKHE Orbital Mesh — Kernel Module
// ============================================================================
// Sincronização de nós orbitais (shards distribuídos). Implementação mínima:
// mantém contagem de nós sincronizados.

use core::sync::atomic::{AtomicU32, Ordering};

/// Malha de nós orbitais.
pub struct OrbitalMesh {
    synced_nodes: AtomicU32,
}

impl OrbitalMesh {
    /// Cria uma malha vazia.
    pub const fn new() -> Self {
        Self {
            synced_nodes: AtomicU32::new(0),
        }
    }

    /// Inicia a sincronização da malha.
    pub fn start_sync(&mut self) {
        self.synced_nodes.store(0, Ordering::SeqCst);
    }

    /// Registra um nó sincronizado.
    pub fn mark_synced(&self) {
        self.synced_nodes.fetch_add(1, Ordering::SeqCst);
    }

    /// Número de nós sincronizados.
    pub fn synced_nodes(&self) -> u32 {
        self.synced_nodes.load(Ordering::SeqCst)
    }
}

impl Default for OrbitalMesh {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mesh_tracks_synced_nodes() {
        let mut m = OrbitalMesh::new();
        m.start_sync();
        assert_eq!(m.synced_nodes(), 0);
        m.mark_synced();
        m.mark_synced();
        assert_eq!(m.synced_nodes(), 2);
    }
}
