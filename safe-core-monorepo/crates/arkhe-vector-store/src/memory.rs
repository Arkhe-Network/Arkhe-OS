use super::*;
use std::collections::HashMap;
use std::sync::Mutex;

pub struct MemoryVectorStore {
    data: Mutex<HashMap<String, VectorPoint>>,
}

impl MemoryVectorStore {
    pub fn new() -> Self {
        Self {
            data: Mutex::new(HashMap::new()),
        }
    }
}

#[async_trait::async_trait]
impl VectorStore for MemoryVectorStore {
    async fn insert(&self, point: VectorPoint) -> VectorStoreResult<()> {
        self.data.lock().unwrap().insert(point.id.clone(), point);
        Ok(())
    }

    async fn search(
        &self,
        vector: &[f32],
        limit: usize,
        _filter: Option<HashMap<String, serde_json::Value>>,
    ) -> VectorStoreResult<Vec<VectorPoint>> {
        // Implementação simplificada: retorna todos os pontos
        // Em produção, faria busca por similaridade real
        let all: Vec<VectorPoint> = self.data.lock().unwrap()
            .values()
            .cloned()
            .take(limit)
            .collect();
        Ok(all)
    }

    async fn get(&self, id: &str) -> VectorStoreResult<VectorPoint> {
        let data = self.data.lock().unwrap();
        data.get(id)
            .cloned()
            .ok_or_else(|| VectorStoreError::NotFound(id.into()))
    }

    async fn delete(&self, id: &str) -> VectorStoreResult<()> {
        let mut data = self.data.lock().unwrap();
        if data.remove(id).is_none() {
            return Err(VectorStoreError::NotFound(id.into()));
        }
        Ok(())
    }

    async fn list_ids(&self) -> VectorStoreResult<Vec<String>> {
        let data = self.data.lock().unwrap();
        Ok(data.keys().cloned().collect())
    }
}
