use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MemoryLevel {
    M0,
    M1,
    M2,
    M3,
    M4,
}

impl MemoryLevel {
    pub fn is_plurality_mapped(&self) -> bool {
        matches!(self, Self::M1 | Self::M2 | Self::M3)
    }

    pub fn default_bucket(&self) -> Option<&'static str> {
        match self {
            Self::M1 => Some("work"),
            Self::M2 => Some("personal"),
            Self::M3 => Some("knowledge"),
            _ => None,
        }
    }

    pub fn is_externally_backed(&self) -> bool {
        self.is_plurality_mapped()
    }
}

#[derive(Debug, Clone)]
pub struct MemoryBlock {
    pub id: String,
    pub level: MemoryLevel,
    pub content: Vec<u8>,
    pub metadata: MemoryMetadata,
    pub source: MemorySource,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub accessed_at: chrono::DateTime<chrono::Utc>,
    pub access_count: u64,
}

#[derive(Debug, Clone, Default)]
pub struct MemoryMetadata {
    pub title: Option<String>,
    pub tags: Vec<String>,
    pub content_type: String,
    pub size_bytes: usize,
    pub checksum: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum MemorySource {
    Cache,
    Plurality,
    External,
}
