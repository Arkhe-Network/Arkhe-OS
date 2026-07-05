#![warn(missing_docs)]

//! Bill of Materials — geração e verificação de CycloneDX ML-BOM.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Component {
    pub name: String,
    pub version: String,
    pub component_type: ComponentType,
    pub purl: Option<String>,
    pub hashes: Vec<HashEntry>,
    pub licenses: Vec<LicenseEntry>,
    pub properties: HashMap<String, String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ComponentType { Library, Model, Dataset, Container, Firmware }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HashEntry {
    pub alg: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LicenseEntry {
    pub id: Option<String>,
    pub name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Bom {
    pub bom_format: String,
    pub spec_version: String,
    pub serial_number: String,
    pub version: u32,
    pub components: Vec<Component>,
    pub metadata: BomMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BomMetadata {
    pub timestamp: String,
    pub tools: Vec<ToolEntry>,
    pub component: Option<Component>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolEntry {
    pub name: String,
    pub version: Option<String>,
}

impl Bom {
    pub fn new() -> Self {
        Self {
            bom_format: "CycloneDX".into(),
            spec_version: "1.6".into(),
            serial_number: format!("urn:uuid:{}", uuid::Uuid::new_v4()),
            version: 1,
            components: Vec::new(),
            metadata: BomMetadata {
                timestamp: chrono::Utc::now().to_rfc3339(),
                tools: vec![ToolEntry { name: "arkhe-bom".into(), version: Some(env!("CARGO_PKG_VERSION").into()) }],
                component: None,
            },
        }
    }

    pub fn add_component(&mut self, component: Component) {
        self.components.push(component);
    }

    pub fn to_json(&self) -> serde_json::Result<String> {
        serde_json::to_string_pretty(&serde_json::json!({
            "bomFormat": self.bom_format,
            "specVersion": self.spec_version,
            "serialNumber": self.serial_number,
            "version": self.version,
            "metadata": self.metadata,
            "components": self.components,
        }))
    }

    pub fn verify_integrity(&self) -> Vec<String> {
        let mut issues = Vec::new();
        for comp in &self.components {
            if comp.hashes.is_empty() {
                issues.push(format!("Component '{}' has no integrity hashes", comp.name));
            }
        }
        issues
    }
}

impl Default for Bom { fn default() -> Self { Self::new() } }
