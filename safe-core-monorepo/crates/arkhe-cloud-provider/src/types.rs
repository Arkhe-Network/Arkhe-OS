//! Tipos para provedores de nuvem.

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Representação de uma instância (VM).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Instance {
    pub id: String,
    pub name: String,
    pub status: InstanceStatus,
    pub flavor: String,
    pub region: String,
    pub ip_addresses: Vec<String>,
    pub cpu_cores: u64,
    pub memory_gb: u64,
    pub created_at: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
    pub provider: String,
}

impl Instance {
    pub fn new(id: &str, name: &str, region: &str, provider: &str) -> Self {
        Self {
            id: id.to_string(),
            name: name.to_string(),
            status: InstanceStatus::Pending,
            flavor: String::new(),
            region: region.to_string(),
            ip_addresses: Vec::new(),
            cpu_cores: 0,
            memory_gb: 0,
            created_at: Utc::now(),
            metadata: HashMap::new(),
            provider: provider.to_string(),
        }
    }
}

/// Status da instância.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum InstanceStatus {
    Pending,
    Running,
    Stopped,
    Suspended,
    Terminated,
    Error,
}

/// Especificação para criar uma nova instância.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstanceSpec {
    pub name: String,
    pub image_id: String,
    pub flavor_id: String,
    pub region: String,
    pub network_ids: Vec<String>,
    pub ssh_key: Option<String>,
    pub user_data: Option<String>,
    pub metadata: HashMap<String, String>,
}

/// Rede.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Network {
    pub id: String,
    pub name: String,
    pub cidr: String,
    pub gateway: String,
    pub region: String,
}

/// Volume de armazenamento.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Volume {
    pub id: String,
    pub name: String,
    pub size_gb: u64,
    pub status: VolumeStatus,
    pub attached_to: Option<String>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum VolumeStatus {
    Available,
    InUse,
    Creating,
    Deleting,
    Error,
}

/// Métricas do cluster.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterMetrics {
    pub total_cpu_cores: u64,
    pub used_cpu_cores: u64,
    pub total_memory_gb: u64,
    pub used_memory_gb: u64,
    pub total_storage_gb: u64,
    pub used_storage_gb: u64,
    pub region: String,
}
