//! Carregadores de documentos com detecção de PII e políticas.

use async_trait::async_trait;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use arkhe_policy_gateway::{PolicyGateway, PolicyInput, GatewayVerdict};

#[derive(Debug, Clone)]
pub struct Document {
    pub id: String,
    pub content: String,
    pub metadata: HashMap<String, String>,
    pub pii_detected: Vec<PiiType>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum PiiType {
    Email,
    Phone,
    Ssn,
    CreditCard,
    Name,
    Address,
}

impl PiiType {
    pub fn pattern(&self) -> Regex {
        match self {
            Self::Email => Regex::new(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}").unwrap(),
            Self::Phone => Regex::new(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}").unwrap(),
            Self::Ssn => Regex::new(r"\d{3}-\d{2}-\d{4}").unwrap(),
            Self::CreditCard => Regex::new(r"\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}").unwrap(),
            Self::Name => Regex::new(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b").unwrap(),
            Self::Address => Regex::new(r"\d+ [A-Za-z ]+ (Street|St|Avenue|Ave|Road|Rd|Drive|Dr)").unwrap(),
        }
    }
}

/// Scannear PII em um documento.
pub fn scan_pii(content: &str) -> Vec<PiiType> {
    let mut detected = Vec::new();
    for pii in [
        PiiType::Email,
        PiiType::Phone,
        PiiType::Ssn,
        PiiType::CreditCard,
        PiiType::Name,
        PiiType::Address,
    ] {
        if pii.pattern().is_match(content) {
            detected.push(pii);
        }
    }
    detected
}

/// Trait para carregadores de documentos.
#[async_trait]
pub trait DocumentLoader: Send + Sync {
    async fn load(&self, source: &str) -> Result<Vec<Document>, String>;
    fn name(&self) -> &str;
}

/// Carregador com verificação de política e PII.
pub struct GovernedLoader<L: DocumentLoader> {
    inner: L,
    gateway: PolicyGateway,
}

impl<L: DocumentLoader> GovernedLoader<L> {
    pub fn new(inner: L, gateway: PolicyGateway) -> Self {
        Self { inner, gateway }
    }

    pub async fn load_with_policy(&self, source: &str, actor: &str) -> Result<Vec<Document>, String> {
        // 1. Verificar política
        let input = PolicyInput {
            actor_did: actor.into(),
            action: "load_document".into(),
            resource: self.inner.name().into(),
            admin_mode: false,
            attributes: {
                let mut m = HashMap::new();
                m.insert("source".into(), serde_json::json!(source));
                m
            },
        };
        let decision = self.gateway.evaluate(&input)
            .map_err(|e| format!("Gateway error: {}", e))?;
        if decision.verdict != GatewayVerdict::Allow {
            return Err(format!("Policy denied: {}", decision.reason));
        }

        // 2. Carregar documentos
        let docs = self.inner.load(source).await?;

        // 3. Scannear PII
        let mut result = Vec::new();
        for mut doc in docs {
            doc.pii_detected = scan_pii(&doc.content);
            if !doc.pii_detected.is_empty() {
                // Registrar em auditoria (simplificado)
                tracing::warn!(
                    actor = actor,
                    doc_id = doc.id,
                    pii = ?doc.pii_detected,
                    "PII detected in document"
                );
            }
            result.push(doc);
        }
        Ok(result)
    }
}

// Loaders concretos (exemplo para texto)
pub struct TextLoader;

#[async_trait]
impl DocumentLoader for TextLoader {
    async fn load(&self, source: &str) -> Result<Vec<Document>, String> {
        let content = std::fs::read_to_string(source)
            .map_err(|e| e.to_string())?;
        Ok(vec![Document {
            id: source.into(),
            content,
            metadata: HashMap::new(),
            pii_detected: Vec::new(),
        }])
    }
    fn name(&self) -> &str { "text" }
}
