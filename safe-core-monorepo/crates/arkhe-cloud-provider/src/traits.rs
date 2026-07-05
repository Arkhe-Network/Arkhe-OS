//! Trait unificado para provedores de nuvem federados.

use async_trait::async_trait;
use crate::types::{Instance, InstanceSpec, InstanceStatus, Network, Volume, ClusterMetrics};
use arkhe_core::ArkheResult;

/// Trait unificado para provedores de nuvem federados.
/// Alinhado com o padrão IEEE 2302 (SIIF) para Intercloud Interoperability.
#[async_trait]
pub trait CloudProvider: Send + Sync {
    /// Nome do provedor (ex: "opennebula", "egi").
    fn provider_name(&self) -> &str;

    /// Jurisdição geográfica do provedor ("EU", "BR", "US", etc.).
    /// Essencial para políticas de soberania de dados (GDPR).
    fn jurisdiction(&self) -> &str;

    /// Lista instâncias (VMs) em uma região.
    async fn list_instances(&self, region: Option<&str>) -> ArkheResult<Vec<Instance>>;

    /// Cria uma nova instância.
    async fn create_instance(&self, spec: &InstanceSpec) -> ArkheResult<Instance>;

    /// Obtém detalhes de uma instância específica.
    async fn get_instance(&self, id: &str) -> ArkheResult<Instance>;

    /// Controla uma instância (start, stop, reboot, suspend).
    async fn control_instance(&self, id: &str, action: InstanceAction) -> ArkheResult<Instance>;

    /// Remove uma instância.
    async fn delete_instance(&self, id: &str) -> ArkheResult<()>;

    /// Lista redes disponíveis.
    async fn list_networks(&self) -> ArkheResult<Vec<Network>>;

    /// Cria um volume de armazenamento.
    async fn create_volume(&self, name: &str, size_gb: u64) -> ArkheResult<Volume>;

    /// Anexa um volume a uma instância.
    async fn attach_volume(&self, instance_id: &str, volume_id: &str) -> ArkheResult<()>;

    /// Métricas do cluster.
    async fn cluster_metrics(&self) -> ArkheResult<ClusterMetrics>;

    /// Verifica se o provedor está acessível.
    async fn health_check(&self) -> ArkheResult<bool>;
}

/// Ações de controle de instância.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstanceAction {
    Start,
    Stop,
    Reboot,
    Suspend,
}
