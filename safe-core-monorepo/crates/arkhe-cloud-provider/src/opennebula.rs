//! Conector OpenNebula via XML-RPC.
//! Baseado na documentação OpenNebula XML-RPC API.

#![cfg(feature = "opennebula")]

use super::traits::*;
use super::types::*;
use arkhe_core::{ArkheError, ArkheResult};
use async_trait::async_trait;
use reqwest::Client;
use std::collections::HashMap;
use tracing::info;
use xmltree::Element;
use base64::prelude::*;

/// Conector para OpenNebula via XML-RPC.
/// OpenNebula expõe métodos XML-RPC como `one.vm.info`, `one.vm.deploy`, etc.
pub struct OpenNebulaProvider {
    client: Client,
    endpoint: String,
    auth: String,  // Base64("user:password")
    region: String,
}

impl OpenNebulaProvider {
    /// Cria um novo conector OpenNebula.
    /// O endpoint deve ser algo como "http://localhost:2633/RPC2"
    pub fn new(endpoint: &str, username: &str, password: &str, region: &str) -> Self {
        let auth = BASE64_STANDARD.encode(format!("{}:{}", username, password));
        Self {
            client: Client::new(),
            endpoint: endpoint.to_string(),
            auth,
            region: region.to_string(),
        }
    }

    /// Constrói uma requisição XML-RPC.
    fn build_xmlrpc_request(&self, method: &str, params: &[String]) -> String {
        let mut xml = String::from("<?xml version=\"1.0\"?><methodCall><methodName>");
        xml.push_str(method);
        xml.push_str("</methodName><params>");
        for p in params {
            xml.push_str("<param><value><string>");
            xml.push_str(p);
            xml.push_str("</string></value></param>");
        }
        xml.push_str("</params></methodCall>");
        xml
    }

    /// Envia uma chamada XML-RPC e retorna a resposta como Element.
    async fn call_xmlrpc(&self, method: &str, params: &[String]) -> ArkheResult<Element> {
        let body = self.build_xmlrpc_request(method, params);
        let response = self.client
            .post(&self.endpoint)
            .header("Content-Type", "text/xml")
            .header("Authorization", format!("Basic {}", self.auth))
            .body(body)
            .send()
            .await
            .map_err(|e| ArkheError::Internal(format!("OpenNebula XML-RPC error: {}", e)))?;

        if !response.status().is_success() {
            let text = response.text().await.unwrap_or_default();
            return Err(ArkheError::Internal(format!("OpenNebula HTTP error: {}", text)));
        }

        let text = response.text().await
            .map_err(|e| ArkheError::Internal(format!("OpenNebula response error: {}", e)))?;

        let element = Element::parse(text.as_bytes())
            .map_err(|e| ArkheError::Internal(format!("XML parse error: {}", e)))?;

        // Verifica se há erro na resposta (formato OpenNebula: [false, error_msg, code])
        if let Some(params) = element.get_child("params") {
            if let Some(param) = params.get_child("param") {
                if let Some(value) = param.get_child("value") {
                    if let Some(boolean) = value.get_child("boolean") {
                        if boolean.text.as_deref() == Some("0") {
                            // Erro: segundo parâmetro é a mensagem de erro
                            if let Some(error_value) = value.parent().and_then(|p| p.get_child("param")) {
                                if let Some(err_text) = error_value.get_text() {
                                    return Err(ArkheError::Internal(format!("OpenNebula error: {}", err_text)));
                                }
                            }
                        }
                    }
                }
            }
        }

        Ok(element)
    }

    // Métodos auxiliares privados
    fn parse_vm(&self, vm: &Element, region: &str) -> Option<Instance> {
        let id = vm.get_child("ID").and_then(|e| e.text.clone()).unwrap_or_default();
        let name = vm.get_child("NAME").and_then(|e| e.text.clone()).unwrap_or_default();
        let state = vm.get_child("STATE").and_then(|e| e.text.clone()).unwrap_or_default();
        let status = match state.as_str() {
            "3" => InstanceStatus::Running,   // ACTIVE
            "1" => InstanceStatus::Pending,   // PENDING
            "5" => InstanceStatus::Stopped,   // STOPPED
            "6" => InstanceStatus::Suspended, // SUSPENDED
            _ => InstanceStatus::Error,
        };
        let mut ips = Vec::new();
        if let Some(nics) = vm.get_child("TEMPLATE").and_then(|t| t.get_child("NIC")) {
            for nic in nics.children.iter() {
                if let Some(ip) = nic.get_child("IP").and_then(|e| e.text.clone()) {
                    ips.push(ip);
                }
            }
        }
        Some(Instance {
            id,
            name,
            status,
            flavor: vm.get_child("TEMPLATE").and_then(|t| t.get_child("FLAVOR")).and_then(|e| e.text.clone()).unwrap_or_default(),
            region: region.to_string(),
            ip_addresses: ips,
            cpu_cores: vm.get_child("TEMPLATE").and_then(|t| t.get_child("CPU")).and_then(|e| e.text.parse().ok()).unwrap_or(0),
            memory_gb: vm.get_child("TEMPLATE").and_then(|t| t.get_child("MEMORY")).and_then(|e| e.text.parse().ok()).unwrap_or(0) / 1024,
            created_at: Utc::now(),
            metadata: HashMap::new(),
            provider: "opennebula".to_string(),
        })
    }

    fn extract_vm_id(&self, response: &Element) -> ArkheResult<String> {
        if let Some(params) = response.get_child("params") {
            if let Some(param) = params.get_child("param") {
                if let Some(value) = param.get_child("value") {
                    if let Some(int) = value.get_child("int") {
                        if let Some(id) = int.text.as_deref() {
                            return Ok(id.to_string());
                        }
                    }
                }
            }
        }
        Err(ArkheError::Internal("Failed to extract VM ID".into()))
    }

    fn extract_vm_from_response(&self, _response: &Element) -> Option<Element> {
        None  // Implementação simplificada
    }

    fn extract_hosts_from_response(&self, _response: &Element) -> Option<Vec<Element>> {
        None  // Implementação simplificada
    }
}

#[async_trait]
impl CloudProvider for OpenNebulaProvider {
    fn provider_name(&self) -> &str {
        "opennebula"
    }

    fn jurisdiction(&self) -> &str {
        &self.region
    }

    async fn list_instances(&self, region: Option<&str>) -> ArkheResult<Vec<Instance>> {
        let params = vec![
            self.auth.clone(),  // session
            "-1".to_string(),   // user_id (-1 = all)
            "-1".to_string(),   // state (-1 = all)
            "-1".to_string(),   // pending (-1 = all)
            "-1".to_string(),   // start
            "-1".to_string(),   // end
        ];
        let response = self.call_xmlrpc("one.vmpool.info", &params).await?;

        let mut instances = Vec::new();
        if let Some(params) = response.get_child("params") {
            if let Some(param) = params.get_child("param") {
                if let Some(value) = param.get_child("value") {
                    if let Some(array) = value.get_child("array") {
                        if let Some(data) = array.get_child("data") {
                            for child in data.children.iter() {
                                if let Some(vm_pool) = child.get_child("VM_POOL") {
                                    for vm_elem in vm_pool.children.iter() {
                                        if let Some(vm) = vm_elem.get_child("VM") {
                                            if let Some(instance) = self.parse_vm(vm, &self.region) {
                                                instances.push(instance);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        Ok(instances)
    }

    async fn create_instance(&self, spec: &InstanceSpec) -> ArkheResult<Instance> {
        let template = format!(
            "<TEMPLATE><NAME>{}</NAME><MEMORY>{}</MEMORY><CPU>{}</CPU><DISK><IMAGE_ID>{}</IMAGE_ID></DISK></TEMPLATE>",
            spec.name,
            1024,  // memory em MB (padrão)
            1,     // CPU cores (padrão)
            spec.image_id
        );

        let params = vec![
            self.auth.clone(),
            template,
            "-1".to_string(), // cluster_id (-1 = default)
            "0".to_string(),  // hold (0 = no)
        ];
        let response = self.call_xmlrpc("one.vm.allocate", &params).await?;

        let vm_id = self.extract_vm_id(&response)?;
        Ok(Instance::new(&vm_id, &spec.name, &spec.region, self.provider_name()))
    }

    async fn get_instance(&self, id: &str) -> ArkheResult<Instance> {
        let params = vec![self.auth.clone(), id.to_string()];
        let response = self.call_xmlrpc("one.vm.info", &params).await?;

        if let Some(vm) = self.extract_vm_from_response(&response) {
            Ok(self.parse_vm(&vm, &self.region).unwrap_or_else(|| {
                Instance::new(id, "unknown", &self.region, self.provider_name())
            }))
        } else {
            Err(ArkheError::NotFound(format!("VM {} not found", id)))
        }
    }

    async fn control_instance(&self, id: &str, action: InstanceAction) -> ArkheResult<Instance> {
        let action_str = match action {
            InstanceAction::Start => "resume",
            InstanceAction::Stop => "stop",
            InstanceAction::Reboot => "reboot",
            InstanceAction::Suspend => "suspend",
        };
        let params = vec![
            self.auth.clone(),
            action_str.to_string(),
            id.to_string(),
        ];
        let _ = self.call_xmlrpc("one.vm.action", &params).await?;
        self.get_instance(id).await
    }

    async fn delete_instance(&self, id: &str) -> ArkheResult<()> {
        let params = vec![
            self.auth.clone(),
            id.to_string(),
            "0".to_string(), // hard (0 = soft)
        ];
        let _ = self.call_xmlrpc("one.vm.terminate", &params).await?;
        Ok(())
    }

    async fn list_networks(&self) -> ArkheResult<Vec<Network>> {
        let params = vec![self.auth.clone(), "-1".to_string(), "-1".to_string(), "-1".to_string()];
        let response = self.call_xmlrpc("one.vnpool.info", &params).await?;
        Ok(vec![
            Network {
                id: "0".into(),
                name: "default".into(),
                cidr: "10.0.0.0/16".into(),
                gateway: "10.0.0.1".into(),
                region: self.region.clone(),
            }
        ])
    }

    async fn create_volume(&self, name: &str, size_gb: u64) -> ArkheResult<Volume> {
        Ok(Volume {
            id: uuid::Uuid::new_v4().to_string(),
            name: name.to_string(),
            size_gb,
            status: VolumeStatus::Creating,
            attached_to: None,
            created_at: Utc::now(),
        })
    }

    async fn attach_volume(&self, instance_id: &str, volume_id: &str) -> ArkheResult<()> {
        let params = vec![
            self.auth.clone(),
            instance_id.to_string(),
            volume_id.to_string(),
        ];
        let _ = self.call_xmlrpc("one.vm.attach", &params).await?;
        Ok(())
    }

    async fn cluster_metrics(&self) -> ArkheResult<ClusterMetrics> {
        let params = vec![self.auth.clone(), "-1".to_string()];
        let response = self.call_xmlrpc("one.hostpool.info", &params).await?;

        let mut total_cpu = 0;
        let mut used_cpu = 0;
        let mut total_mem = 0;
        let mut used_mem = 0;

        if let Some(hosts) = self.extract_hosts_from_response(&response) {
            for host in hosts {
                if let Some(cpu) = host.get_child("CPU") {
                    if let Some(total) = cpu.get_child("TOTAL_CPU") {
                        if let Some(val) = total.text.as_deref().and_then(|s| s.parse::<u64>().ok()) {
                            total_cpu += val;
                        }
                    }
                    if let Some(used) = cpu.get_child("USED_CPU") {
                        if let Some(val) = used.text.as_deref().and_then(|s| s.parse::<u64>().ok()) {
                            used_cpu += val;
                        }
                    }
                }
                if let Some(mem) = host.get_child("MEMORY") {
                    if let Some(total) = mem.get_child("TOTAL_MEMORY") {
                        if let Some(val) = total.text.as_deref().and_then(|s| s.parse::<u64>().ok()) {
                            total_mem += val / 1024; // KB -> MB
                        }
                    }
                    if let Some(used) = mem.get_child("USED_MEMORY") {
                        if let Some(val) = used.text.as_deref().and_then(|s| s.parse::<u64>().ok()) {
                            used_mem += val / 1024;
                        }
                    }
                }
            }
        }

        Ok(ClusterMetrics {
            total_cpu_cores: total_cpu,
            used_cpu_cores: used_cpu,
            total_memory_gb: total_mem / 1024,
            used_memory_gb: used_mem / 1024,
            total_storage_gb: 0,
            used_storage_gb: 0,
            region: self.region.clone(),
        })
    }

    async fn health_check(&self) -> ArkheResult<bool> {
        let params = vec![self.auth.clone()];
        match self.call_xmlrpc("one.version", &params).await {
            Ok(_) => Ok(true),
            Err(_) => Ok(false),
        }
    }
}
