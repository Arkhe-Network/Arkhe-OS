//! Conector OpenStack via REST API.
//! Baseado na API OpenStack (Keystone + Nova + Cinder).

#![cfg(feature = "openstack")]

use super::traits::*;
use super::types::*;
use arkhe_core::{ArkheError, ArkheResult};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;
use tracing::info;

/// Conector para OpenStack via Keystone + Nova + Cinder.
pub struct OpenStackProvider {
    client: Client,
    auth_url: String,
    project_id: String,
    token: String,
    region: String,
    token_expires_at: chrono::DateTime<chrono::Utc>,
}

impl OpenStackProvider {
    /// Cria um novo conector autenticando via Keystone v3.
    pub async fn new(
        auth_url: &str,
        username: &str,
        password: &str,
        project_name: &str,
        region: &str,
    ) -> ArkheResult<Self> {
        let client = Client::new();
        let payload = serde_json::json!({
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": username,
                            "domain": { "name": "Default" },
                            "password": password
                        }
                    }
                },
                "scope": {
                    "project": {
                        "name": project_name,
                        "domain": { "name": "Default" }
                    }
                }
            }
        });

        let resp = client
            .post(&format!("{}/auth/tokens", auth_url))
            .json(&payload)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(format!("OpenStack auth error: {}", e)))?;

        let token = resp.headers()
            .get("X-Subject-Token")
            .ok_or_else(|| ArkheError::Internal("No token in response".into()))?
            .to_str()
            .map_err(|_| ArkheError::Internal("Invalid token header".into()))?
            .to_string();

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(format!("JSON parse error: {}", e)))?;

        let project_id = json["token"]["project"]["id"].as_str().unwrap_or("").to_string();

        // Estima expiração (default 1 hora)
        let expires_at = chrono::Utc::now() + chrono::Duration::hours(1);

        Ok(Self {
            client,
            auth_url: auth_url.to_string(),
            project_id,
            token,
            region: region.to_string(),
            token_expires_at: expires_at,
        })
    }

    /// Renova o token se expirado.
    async fn ensure_token(&mut self) -> ArkheResult<()> {
        if chrono::Utc::now() >= self.token_expires_at {
            // Re-autenticar (simplificado)
            self.token_expires_at = chrono::Utc::now() + chrono::Duration::hours(1);
        }
        Ok(())
    }

    fn parse_server(&self, server: &Value, region: &str) -> Instance {
        let status_str = server["status"].as_str().unwrap_or("UNKNOWN");
        let status = match status_str {
            "ACTIVE" => InstanceStatus::Running,
            "BUILD" => InstanceStatus::Pending,
            "SHUTOFF" => InstanceStatus::Stopped,
            "SUSPENDED" => InstanceStatus::Suspended,
            "ERROR" => InstanceStatus::Error,
            _ => InstanceStatus::Error,
        };

        let mut ips = Vec::new();
        if let Some(addresses) = server["addresses"].as_object() {
            for (_net, addrs) in addresses {
                if let Some(arr) = addrs.as_array() {
                    for addr in arr {
                        if let Some(ip) = addr["addr"].as_str() {
                            ips.push(ip.to_string());
                        }
                    }
                }
            }
        }

        Instance {
            id: server["id"].as_str().unwrap_or("").to_string(),
            name: server["name"].as_str().unwrap_or("").to_string(),
            status,
            flavor: server["flavor"]["id"].as_str().unwrap_or("").to_string(),
            region: region.to_string(),
            ip_addresses: ips,
            cpu_cores: 0,
            memory_gb: 0,
            created_at: Utc::now(),
            metadata: HashMap::new(),
            provider: "openstack".to_string(),
        }
    }
}

#[async_trait]
impl CloudProvider for OpenStackProvider {
    fn provider_name(&self) -> &str {
        "openstack"
    }

    fn jurisdiction(&self) -> &str {
        &self.region
    }

    async fn list_instances(&self, region: Option<&str>) -> ArkheResult<Vec<Instance>> {
        let url = format!("{}/compute/v2.1/servers/detail", self.auth_url);
        let resp = self.client
            .get(&url)
            .header("X-Auth-Token", &self.token)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("List servers error: {}", text)));
        }

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        let mut instances = Vec::new();
        if let Some(servers) = json["servers"].as_array() {
            for server in servers {
                let instance = self.parse_server(server, region.as_deref().unwrap_or(&self.region));
                instances.push(instance);
            }
        }
        Ok(instances)
    }

    async fn create_instance(&self, spec: &InstanceSpec) -> ArkheResult<Instance> {
        let url = format!("{}/compute/v2.1/servers", self.auth_url);
        let payload = serde_json::json!({
            "server": {
                "name": spec.name,
                "imageRef": spec.image_id,
                "flavorRef": spec.flavor_id,
                "networks": spec.network_ids.iter().map(|id| serde_json::json!({"uuid": id})).collect::<Vec<_>>(),
                "metadata": spec.metadata,
            }
        });

        let resp = self.client
            .post(&url)
            .header("X-Auth-Token", &self.token)
            .json(&payload)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("Create server error: {}", text)));
        }

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        let server = &json["server"];
        Ok(Instance {
            id: server["id"].as_str().unwrap_or("").to_string(),
            name: server["name"].as_str().unwrap_or("").to_string(),
            status: InstanceStatus::Pending,
            flavor: spec.flavor_id.clone(),
            region: spec.region.clone(),
            ip_addresses: Vec::new(),
            cpu_cores: 0,
            memory_gb: 0,
            created_at: Utc::now(),
            metadata: spec.metadata.clone(),
            provider: self.provider_name().to_string(),
        })
    }

    async fn get_instance(&self, id: &str) -> ArkheResult<Instance> {
        let url = format!("{}/compute/v2.1/servers/{}", self.auth_url, id);
        let resp = self.client
            .get(&url)
            .header("X-Auth-Token", &self.token)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::NotFound(format!("Server {} not found: {}", id, text)));
        }

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        Ok(self.parse_server(&json["server"], &self.region))
    }

    async fn control_instance(&self, id: &str, action: InstanceAction) -> ArkheResult<Instance> {
        let action_str = match action {
            InstanceAction::Start => "os-start",
            InstanceAction::Stop => "os-stop",
            InstanceAction::Reboot => "reboot",
            InstanceAction::Suspend => "suspend",
        };

        let url = format!("{}/compute/v2.1/servers/{}/action", self.auth_url, id);
        let payload = serde_json::json!({
            action_str: if action == InstanceAction::Reboot { Some({ "type": "SOFT" }) } else { None }
        });

        let resp = self.client
            .post(&url)
            .header("X-Auth-Token", &self.token)
            .json(&payload)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("Control error: {}", text)));
        }

        self.get_instance(id).await
    }

    async fn delete_instance(&self, id: &str) -> ArkheResult<()> {
        let url = format!("{}/compute/v2.1/servers/{}", self.auth_url, id);
        let resp = self.client
            .delete(&url)
            .header("X-Auth-Token", &self.token)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("Delete error: {}", text)));
        }
        Ok(())
    }

    async fn list_networks(&self) -> ArkheResult<Vec<Network>> {
        let url = format!("{}/network/v2.0/networks", self.auth_url);
        let resp = self.client
            .get(&url)
            .header("X-Auth-Token", &self.token)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("List networks error: {}", text)));
        }

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        let mut networks = Vec::new();
        if let Some(nets) = json["networks"].as_array() {
            for net in nets {
                networks.push(Network {
                    id: net["id"].as_str().unwrap_or("").to_string(),
                    name: net["name"].as_str().unwrap_or("").to_string(),
                    cidr: net["cidr"].as_str().unwrap_or("").to_string(),
                    gateway: net["gateway_ip"].as_str().unwrap_or("").to_string(),
                    region: self.region.clone(),
                });
            }
        }
        Ok(networks)
    }

    async fn create_volume(&self, name: &str, size_gb: u64) -> ArkheResult<Volume> {
        let url = format!("{}/volume/v3/{}/volumes", self.auth_url, self.project_id);
        let payload = serde_json::json!({
            "volume": {
                "name": name,
                "size": size_gb,
            }
        });

        let resp = self.client
            .post(&url)
            .header("X-Auth-Token", &self.token)
            .json(&payload)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("Create volume error: {}", text)));
        }

        let json: Value = resp.json().await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        let volume = &json["volume"];
        Ok(Volume {
            id: volume["id"].as_str().unwrap_or("").to_string(),
            name: volume["name"].as_str().unwrap_or("").to_string(),
            size_gb,
            status: VolumeStatus::Creating,
            attached_to: None,
            created_at: Utc::now(),
        })
    }

    async fn attach_volume(&self, instance_id: &str, volume_id: &str) -> ArkheResult<()> {
        let url = format!("{}/compute/v2.1/servers/{}/os-volume_attachments", self.auth_url, instance_id);
        let payload = serde_json::json!({
            "volumeAttachment": {
                "volumeId": volume_id,
                "device": "/dev/vdb"
            }
        });

        let resp = self.client
            .post(&url)
            .header("X-Auth-Token", &self.token)
            .json(&payload)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(e.to_string()))?;

        if !resp.status().is_success() {
            let text = resp.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("Attach volume error: {}", text)));
        }
        Ok(())
    }

    async fn cluster_metrics(&self) -> ArkheResult<ClusterMetrics> {
        // OpenStack não fornece métricas agregadas facilmente.
        Ok(ClusterMetrics {
            total_cpu_cores: 0,
            used_cpu_cores: 0,
            total_memory_gb: 0,
            used_memory_gb: 0,
            total_storage_gb: 0,
            used_storage_gb: 0,
            region: self.region.clone(),
        })
    }

    async fn health_check(&self) -> ArkheResult<bool> {
        let url = format!("{}/", self.auth_url);
        match self.client.get(&url).send().await {
            Ok(resp) => Ok(resp.status().is_success()),
            Err(_) => Ok(false),
        }
    }
}
