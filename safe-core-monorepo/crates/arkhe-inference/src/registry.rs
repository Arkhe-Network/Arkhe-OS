use serde::{Deserialize, Serialize};
use std::fmt;

/// Identificador único de modelo: `family/name`.
#[derive(Debug, Clone, Hash, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModelId {
    family: String,
    name: String,
}

impl ModelId {
    pub fn new(family: &str, name: &str) -> Self {
        Self { family: family.to_string(), name: name.to_string() }
    }
    pub fn family(&self) -> &str { &self.family }
    pub fn name(&self) -> &str { &self.name }
    pub fn as_str(&self) -> String { format!("{}/{}", self.family, self.name) }
}

impl fmt::Display for ModelId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}", self.family, self.name)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BackendType {
    Null,
    MistralRs,
    Candle,
    LlamaCpp,
    Remote,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCapabilities {
    pub chat: bool,
    pub completion: bool,
    pub tools: bool,
    pub vision: bool,
    pub streaming: bool,
    pub max_context_tokens: u32,
}

impl Default for ModelCapabilities {
    fn default() -> Self {
        Self { chat: true, completion: false, tools: false, vision: false, streaming: false, max_context_tokens: 4096 }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelLicense {
    pub name: String,
    pub commercial_use: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelEntry {
    pub id: ModelId,
    pub backend: BackendType,
    pub capabilities: ModelCapabilities,
    pub license: ModelLicense,
    pub path: Option<String>,
}

/// Registro de modelos disponíveis.
pub struct ModelRegistry {
    models: Vec<ModelEntry>,
}

impl ModelRegistry {
    pub fn new() -> Self { Self { models: Vec::new() } }

    pub fn register(&mut self, entry: ModelEntry) {
        self.models.push(entry);
    }

    pub fn get(&self, id: &ModelId) -> Option<&ModelEntry> {
        self.models.iter().find(|m| &m.id == id)
    }

    pub fn list(&self) -> &[ModelEntry] { &self.models }

    pub fn find_by_backend(&self, backend: BackendType) -> Vec<&ModelEntry> {
        self.models.iter().filter(|m| m.backend == backend).collect()
    }
}

impl Default for ModelRegistry {
    fn default() -> Self { Self::new() }
}
