// crates/arkhe-deploy/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Deploy declarativo para Arkhe OS — inspirado em NixOS.
//!
//! Princípios (direto do manifesto Proxmox+NixOS):
//!
//! 1. **Declarativo**: O estado desejado é descrito em um manifesto JSON/TOML,
//!    não em comandos imperativos.
//! 2. **Imutável**: Cada deploy gera uma "geração" imutável identificada por hash.
//! 3. **Rollbackável**: Voltar para uma geração anterior é uma operação atômica.
//! 4. **Reproduzível**: O mesmo manifesto produz o mesmo resultado,
//!    independentemente do estado atual.
//! 5. **Auditável**: Cada mudança de geração é registrada na AuditTrail.
//!
//! # Fluxo
//!
//! ```text
//! arkhe.nix (manifesto)  →  arkhe-deploy plan   →  diff da geração atual
//!                       →  arkhe-deploy apply   →  nova geração + rollback entry
//!                       →  arkhe-deploy rollback →  geração anterior ativada
//! ```

use arkhe_audit_trail::{AuditCategory, AuditOutcome, AuditTrail, NewAuditEntry};
use blake3::Hash;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DeployError {
    #[error("manifest error: {0}")]
    Manifest(String),

    #[error("generation not found: {id}")]
    GenerationNotFound { id: String },

    #[error("no current generation — nothing to rollback from")]
    NoCurrentGeneration,

    #[error("no previous generation — cannot rollback")]
    NoPreviousGeneration,

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("audit error: {0}")]
    Audit(String),

    #[error("plan error: {0}")]
    Plan(String),
}

pub type DeployResult<T> = Result<T, DeployError>;

/// Manifesto declarativo de deploy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeployManifest {
    /// Versão do formato do manifesto.
    pub version: u32,
    /// Nome do ambiente (ex: "production", "staging", "dev").
    pub environment: String,
    /// Crates a serem compilados com suas features.
    pub crates: Vec<CrateSpec>,
    /// Configurações do sistema.
    pub config: HashMap<String, serde_json::Value>,
    /// Políticas Rego a serem carregadas.
    pub policies: Vec<PolicySpec>,
    /// Metadados livres.
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Especificação de um crate no deploy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CrateSpec {
    /// Nome do crate (ex: "arkhe-policy-gateway").
    pub name: String,
    /// Features a ativar.
    pub features: Vec<String>,
    /// Se deve ser compilado com --release.
    pub release: bool,
}

/// Especificação de uma política Rego.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicySpec {
    /// Nome da política.
    pub name: String,
    /// Código-fonte Rego.
    pub source: String,
    /// Caminho para arquivo (alternativa a source inline).
    pub path: Option<String>,
}

impl DeployManifest {
    /// Cria manifesto mínimo para desenvolvimento.
    pub fn dev() -> Self {
        Self {
            version: 1,
            environment: "dev".into(),
            crates: vec![],
            config: HashMap::new(),
            policies: vec![],
            metadata: HashMap::new(),
        }
    }

    /// Cria manifesto a partir de JSON.
    pub fn from_json(json: &str) -> DeployResult<Self> {
        serde_json::from_str(json)
            .map_err(|e| DeployError::Manifest(format!("invalid JSON: {}", e)))
    }

    /// Serializa para JSON.
    pub fn to_json(&self) -> DeployResult<String> {
        serde_json::to_string_pretty(self)
            .map_err(|e| DeployError::Manifest(format!("serialization failed: {}", e)))
    }

    /// Calcula o hash do manifesto (identifica a geração).
    pub fn hash(&self) -> GenerationId {
        let json = self.to_json().unwrap_or_default();
        let hash = blake3::hash(json.as_bytes());
        GenerationId(hash.to_string())
    }
}

/// ID de uma geração de deploy (blake3 hash do manifesto).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct GenerationId(pub String);

impl std::fmt::Display for GenerationId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        // Primeiros 16 chars do hash
        write!(f, "{}", &self.0[..self.0.len().min(16)])
    }
}

/// Estado de uma geração de deploy.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Generation {
    /// ID único (hash do manifesto).
    pub id: GenerationId,
    /// Manifesto que gerou esta geração.
    pub manifest: DeployManifest,
    /// Timestamp de criação.
    pub created_at: DateTime<Utc>,
    /// Se esta é a geração atualmente ativa.
    pub active: bool,
    /// Hash da geração anterior (para cadeia de rollbacks).
    pub previous_generation: Option<GenerationId>,
}

impl Generation {
    /// Cria uma nova geração a partir de um manifesto.
    pub fn new(manifest: DeployManifest, previous: Option<&Generation>) -> Self {
        Self {
            id: manifest.hash(),
            manifest,
            created_at: Utc::now(),
            active: false,
            previous_generation: previous.map(|g| g.id.clone()),
        }
    }
}

/// Plano de deploy (diff entre gerações).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeployPlan {
    /// Geração atual.
    pub current: Option<GenerationId>,
    /// Geração alvo.
    pub target: GenerationId,
    /// Mudanças detectadas.
    pub changes: Vec<PlanChange>,
    /// Se é um rollback.
    pub is_rollback: bool,
}

/// Uma mudança individual no plano.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanChange {
    /// Tipo da mudança.
    pub kind: ChangeKind,
    /// O que mudou.
    pub description: String,
}

/// Tipo de mudança.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ChangeKind {
    /// Crate adicionado.
    CrateAdded,
    /// Crate removido.
    CrateRemoved,
    /// Feature alterada.
    FeatureChanged,
    /// Config alterada.
    ConfigChanged,
    /// Política adicionada.
    PolicyAdded,
    /// Política removida.
    PolicyRemoved,
    /// Política modificada.
    PolicyModified,
    /// Ambiente mudou.
    EnvironmentChanged,
    /// Nenhuma mudança.
    NoChange,
}

/// Gerenciador de deploys.
pub struct DeployManager {
    /// Todas as gerações conhecidas.
    generations: HashMap<GenerationId, Generation>,
    /// Geração atualmente ativa.
    current: Option<GenerationId>,
    /// Ordem cronológica das gerações.
    chronological_order: Vec<GenerationId>,
    /// Trilha de auditoria.
    audit_trail: std::sync::Mutex<AuditTrail>,
    /// Diretório de estado.
    state_dir: Option<PathBuf>,
}

impl DeployManager {
    /// Cria gerenciador vazio (in-memory).
    pub fn new() -> Self {
        Self {
            generations: HashMap::new(),
            current: None,
            chronological_order: Vec::new(),
            audit_trail: std::sync::Mutex::new(AuditTrail::new()),
            state_dir: None,
        }
    }

    /// Cria gerenciador com persistência em diretório.
    pub fn with_state_dir(dir: &Path) -> DeployResult<Self> {
        std::fs::create_dir_all(dir)?;
        Ok(Self {
            state_dir: Some(dir.to_path_buf()),
            ..Self::new()
        })
    }

    /// Calcula o plano de deploy (dry-run).
    pub fn plan(&self, manifest: &DeployManifest) -> DeployResult<DeployPlan> {
        let target_id = manifest.hash();
        let current_id = self.current.clone();
        let is_rollback = match &current_id {
            Some(id) => self.chronological_order.contains(&target_id) &&
                self.chronological_order.iter().position(|x| x == id)
                    .map(|pos| self.chronological_order.iter().position(|x| x == &target_id).map(|tpos| tpos < pos))
                    .flatten()
                    .unwrap_or(false),
            None => false,
        };

        let changes = match &current_id {
            None => {
                // Primeiro deploy
                let mut changes = Vec::new();
                for c in &manifest.crates {
                    changes.push(PlanChange {
                        kind: ChangeKind::CrateAdded,
                        description: format!("+ {} (features: {:?}, release: {})", c.name, c.features, c.release),
                    });
                }
                for p in &manifest.policies {
                    changes.push(PlanChange {
                        kind: ChangeKind::PolicyAdded,
                        description: format!("+ policy: {}", p.name),
                    });
                }
                if !changes.is_empty() {
                    changes.insert(0, PlanChange {
                        kind: ChangeKind::NoChange,
                        description: "Initial deployment".into(),
                    });
                }
                changes
            }
            Some(cur_id) => {
                let current = self.generations.get(cur_id)
                    .ok_or(DeployError::GenerationNotFound { id: cur_id.0.clone() })?;

                if cur_id == &target_id {
                    vec![PlanChange {
                        kind: ChangeKind::NoChange,
                        description: "No changes — manifest is identical to current generation".into(),
                    }]
                } else {
                    self.diff_manifests(&current.manifest, manifest)
                }
            }
        };

        Ok(DeployPlan {
            current: current_id,
            target: target_id,
            changes,
            is_rollback,
        })
    }

    /// Aplica um deploy (cria nova geração).
    pub fn apply(&mut self, manifest: DeployManifest) -> DeployResult<Generation> {
        let plan = self.plan(&manifest)?;
        let previous = self.current.as_ref()
            .and_then(|id| self.generations.get(id))
            .cloned();

        let mut generation = Generation::new(manifest, previous.as_ref());

        if plan.changes.iter().all(|c| c.kind == ChangeKind::NoChange) {
            // Nenhuma mudança — reativa a geração existente
            if let Some(cur_id) = &self.current {
                if let Some(gen) = self.generations.get_mut(cur_id) {
                    gen.active = true;
                    return Ok(gen.clone());
                }
            }
        }

        // Desativar geração anterior
        if let Some(cur_id) = &self.current {
            if let Some(gen) = self.generations.get_mut(cur_id) {
                gen.active = false;
            }
        }

        generation.active = true;
        let id = generation.id.clone();

        // Persistir
        if let Some(ref dir) = self.state_dir {
            self.persist_generation(&generation, dir)?;
        }

        self.chronological_order.push(id.clone());
        self.generations.insert(id.clone(), generation.clone());
        self.current = Some(id);

        // Auditoria
        self.audit_apply(&generation, &plan)?;

        Ok(generation)
    }

    /// Rollback para a geração anterior.
    pub fn rollback(&mut self) -> DeployResult<Generation> {
        let current_id = self.current
            .as_ref()
            .ok_or(DeployError::NoCurrentGeneration)?;

        let current = self.generations.get(current_id)
            .ok_or(DeployError::GenerationNotFound { id: current_id.0.clone() })?;

        let prev_id = current.previous_generation.as_ref()
            .ok_or(DeployError::NoPreviousGeneration)?;

        let prev = self.generations.get(prev_id)
            .ok_or(DeployError::GenerationNotFound { id: prev_id.0.clone() })?
            .clone();

        // Desativar atual
        if let Some(gen) = self.generations.get_mut(current_id) {
            gen.active = false;
        }

        // Reativar anterior (cria nova geração que aponta para anterior)
        let rollback_manifest = prev.manifest.clone();
        let mut rollback_gen = Generation::new(rollback_manifest, Some(&prev));
        rollback_gen.active = true;
        let rollback_id = rollback_gen.id.clone();

        self.chronological_order.push(rollback_id.clone());
        self.generations.insert(rollback_id.clone(), rollback_gen.clone());
        self.current = Some(rollback_id);

        // Auditoria
        self.audit_rollback(&prev)?;

        Ok(rollback_gen)
    }

    /// Rollback para geração específica.
    pub fn rollback_to(&mut self, target_id: &GenerationId) -> DeployResult<Generation> {
        if !self.generations.contains_key(target_id) {
            return Err(DeployError::GenerationNotFound { id: target_id.0.clone() });
        }

        // Desativar atual
        if let Some(cur_id) = &self.current {
            if let Some(gen) = self.generations.get_mut(cur_id) {
                gen.active = false;
            }
        }

        let target = self.generations.get(target_id).unwrap().clone();
        let mut reactivation = Generation::new(target.manifest.clone(), Some(&target));
        reactivation.active = true;
        let reactivation_id = reactivation.id.clone();

        self.chronological_order.push(reactivation_id.clone());
        self.generations.insert(reactivation_id.clone(), reactivation.clone());
        self.current = Some(reactivation_id);

        self.audit_rollback(&target)?;

        Ok(reactivation)
    }

    /// Lista histórico de gerações (mais recente primeiro).
    pub fn history(&self) -> Vec<&Generation> {
        self.chronological_order
            .iter()
            .rev()
            .filter_map(|id| self.generations.get(id))
            .collect()
    }

    /// Geração atual.
    pub fn current(&self) -> Option<&Generation> {
        self.current.as_ref().and_then(|id| self.generations.get(id))
    }

    /// Número total de gerações.
    pub fn generation_count(&self) -> usize {
        self.generations.len()
    }

    /// Acesso à trilha de auditoria.
    pub fn audit_trail(&self) -> std::sync::MutexGuard<'_, AuditTrail> {
        self.audit_trail.lock().unwrap()
    }

    fn diff_manifests(&self, current: &DeployManifest, target: &DeployManifest) -> Vec<PlanChange> {
        let mut changes = Vec::new();

        if current.environment != target.environment {
            changes.push(PlanChange {
                kind: ChangeKind::EnvironmentChanged,
                description: format!("environment: {} → {}", current.environment, target.environment),
            });
        }

        // Crates adicionados
        let current_crates: std::collections::HashSet<_> = current.crates.iter().map(|c| &c.name).collect();
        for c in &target.crates {
            if !current_crates.contains(&c.name) {
                changes.push(PlanChange {
                    kind: ChangeKind::CrateAdded,
                    description: format!("+ {}", c.name),
                });
            }
        }

        // Crates removidos
        let target_crates: std::collections::HashSet<_> = target.crates.iter().map(|c| &c.name).collect();
        for c in &current.crates {
            if !target_crates.contains(&c.name) {
                changes.push(PlanChange {
                    kind: ChangeKind::CrateRemoved,
                    description: format!("- {}", c.name),
                });
            }
        }

        // Features alteradas
        for tc in &target.crates {
            if let Some(cc) = current.crates.iter().find(|c| c.name == tc.name) {
                if cc.features != tc.features || cc.release != tc.release {
                    changes.push(PlanChange {
                        kind: ChangeKind::FeatureChanged,
                        description: format!("~ {} features: {:?} → {:?}, release: {} → {}",
                            tc.name, cc.features, tc.features, cc.release, tc.release),
                    });
                }
            }
        }

        // Config alterada
        for (key, val) in &target.config {
            if current.config.get(key) != Some(val) {
                changes.push(PlanChange {
                    kind: ChangeKind::ConfigChanged,
                    description: format!("~ config.{} = {}", key, serde_json::to_string(val).unwrap_or_default()),
                });
            }
        }
        for key in current.config.keys() {
            if !target.config.contains_key(key) {
                changes.push(PlanChange {
                    kind: ChangeKind::ConfigChanged,
                    description: format!("- config.{} (removed)", key),
                });
            }
        }

        // Políticas
        let current_policies: std::collections::HashSet<_> = current.policies.iter().map(|p| &p.name).collect();
        for p in &target.policies {
            if !current_policies.contains(&p.name) {
                changes.push(PlanChange {
                    kind: ChangeKind::PolicyAdded,
                    description: format!("+ policy: {}", p.name),
                });
            } else if let Some(cp) = current.policies.iter().find(|pp| pp.name == p.name) {
                if cp.source != p.source {
                    changes.push(PlanChange {
                        kind: ChangeKind::PolicyModified,
                        description: format!("~ policy: {}", p.name),
                    });
                }
            }
        }
        for p in &current.policies {
            if !target.policies.iter().any(|pp| pp.name == p.name) {
                changes.push(PlanChange {
                    kind: ChangeKind::PolicyRemoved,
                    description: format!("- policy: {}", p.name),
                });
            }
        }

        if changes.is_empty() {
            changes.push(PlanChange {
                kind: ChangeKind::NoChange,
                description: "No changes detected".into(),
            });
        }

        changes
    }

    fn persist_generation(&self, gen: &Generation, dir: &Path) -> DeployResult<()> {
        let gen_dir = dir.join("generations").join(&gen.id.0);
        std::fs::create_dir_all(&gen_dir)?;
        let json = serde_json::to_string_pretty(gen)
            .map_err(|e| DeployError::Manifest(e.to_string()))?;
        std::fs::write(gen_dir.join("manifest.json"), json)?;
        Ok(())
    }

    fn audit_apply(&self, gen: &Generation, plan: &DeployPlan) -> DeployResult<()> {
        let mut trail = self.audit_trail.lock().map_err(|e| DeployError::Audit(e.to_string()))?;
        let mut details = HashMap::new();
        details.insert("generation_id".into(), serde_json::json!(gen.id.0));
        details.insert("environment".into(), serde_json::json!(gen.manifest.environment));
        details.insert("changes".into(), serde_json::json!(plan.changes.len()));
        details.insert("is_rollback".into(), serde_json::json!(plan.is_rollback));
        details.insert("crate_count".into(), serde_json::json!(gen.manifest.crates.len()));
        details.insert("policy_count".into(), serde_json::json!(gen.manifest.policies.len()));

        trail.record(NewAuditEntry {
            category: AuditCategory::Configuration,
            action: format!("deploy:{}", gen.manifest.environment),
            actor_did: "did:arkhe:deploy".into(),
            resource: gen.id.0.clone(),
            outcome: AuditOutcome::Success,
            details,
        }).map_err(|e| DeployError::Audit(e.to_string()))?;
        Ok(())
    }

    fn audit_rollback(&self, target: &Generation) -> DeployResult<()> {
        let mut trail = self.audit_trail.lock().map_err(|e| DeployError::Audit(e.to_string()))?;
        let mut details = HashMap::new();
        details.insert("target_generation".into(), serde_json::json!(target.id.0));
        details.insert("environment".into(), serde_json::json!(target.manifest.environment));

        trail.record(NewAuditEntry {
            category: AuditCategory::SecurityAlert, // Rollback é evento de segurança
            action: "rollback".into(),
            actor_did: "did:arkhe:deploy".into(),
            resource: target.id.0.clone(),
            outcome: AuditOutcome::Success,
            details,
        }).map_err(|e| DeployError::Audit(e.to_string()))?;
        Ok(())
    }
}

impl Default for DeployManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dev_manifest() -> DeployManifest {
        DeployManifest::dev()
    }

    fn prod_manifest() -> DeployManifest {
        DeployManifest {
            version: 1,
            environment: "production".into(),
            crates: vec![
                CrateSpec { name: "arkhe-policy-gateway".into(), features: vec!["rego".into()], release: true },
                CrateSpec { name: "arkhe-wormgraph-core".into(), features: vec![], release: true },
            ],
            config: {
                let mut m = HashMap::new();
                m.insert("admin_mode".into(), serde_json::json!(false));
                m.insert("log.level".into(), serde_json::json!("info"));
                m
            },
            policies: vec![PolicySpec {
                name: "production_rules".into(),
                source: r#"package arkhe.policy
default allow = false
allow { input.action == "read" }"#.into(),
                path: None,
            }],
            metadata: HashMap::new(),
        }
    }

    #[test]
    fn first_deploy_creates_generation() {
        let mut mgr = DeployManager::new();
        let gen = mgr.apply(dev_manifest()).unwrap();
        assert!(gen.active);
        assert_eq!(mgr.generation_count(), 1);
        assert!(mgr.current().is_some());
    }

    #[test]
    fn same_manifest_no_new_generation() {
        let mut mgr = DeployManager::new();
        let m = dev_manifest();
        mgr.apply(m.clone()).unwrap();
        mgr.apply(m).unwrap();
        // Mesmo hash → reativa, não cria nova
        assert_eq!(mgr.generation_count(), 1);
    }

    #[test]
    fn different_manifest_creates_new_generation() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();
        mgr.apply(prod_manifest()).unwrap();
        assert_eq!(mgr.generation_count(), 2);
    }

    #[test]
    fn plan_detects_changes() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();

        let plan = mgr.plan(&prod_manifest()).unwrap();
        assert!(!plan.changes.iter().all(|c| c.kind == ChangeKind::NoChange));
        assert!(!plan.is_rollback);
    }

    #[test]
    fn plan_no_change() {
        let mut mgr = DeployManager::new();
        let m = dev_manifest();
        mgr.apply(m.clone()).unwrap();

        let plan = mgr.plan(&m).unwrap();
        assert!(plan.changes.iter().all(|c| c.kind == ChangeKind::NoChange));
    }

    #[test]
    fn rollback_to_previous() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();
        let first_id = mgr.current().unwrap().id.clone();

        mgr.apply(prod_manifest()).unwrap();
        assert_ne!(mgr.current().unwrap().id, first_id);

        mgr.rollback().unwrap();
        // Rollback cria nova geração com mesmo conteúdo, hash diferente
        assert!(mgr.current().is_some());
        let current = mgr.current().unwrap();
        assert_eq!(current.manifest.environment, "dev");
    }

    #[test]
    fn rollback_without_previous_fails() {
        let mut mgr = DeployManager::new();
        let result = mgr.rollback();
        assert!(matches!(result, Err(DeployError::NoCurrentGeneration)));
    }

    #[test]
    fn rollback_to_specific_generation() {
        let mut mgr = DeployManager::new();

        let m1 = dev_manifest();
        mgr.apply(m1).unwrap();
        let gen1_id = mgr.current().unwrap().id.clone();

        mgr.apply(prod_manifest()).unwrap();

        let mut m3 = prod_manifest();
        m3.config.insert("extra".into(), serde_json::json!(true));
        mgr.apply(m3).unwrap();

        mgr.rollback_to(&gen1_id).unwrap();
        assert_eq!(mgr.current().unwrap().manifest.environment, "dev");
    }

    #[test]
    fn history_is_chronological_reversed() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();
        mgr.apply(prod_manifest()).unwrap();

        let history = mgr.history();
        assert_eq!(history.len(), 2);
        assert_eq!(history[0].manifest.environment, "production");
        assert_eq!(history[1].manifest.environment, "dev");
    }

    #[test]
    fn apply_audits_to_trail() {
        let mut mgr = DeployManager::new();
        mgr.apply(prod_manifest()).unwrap();
        assert_eq!(mgr.audit_trail().len(), 1);
        assert_eq!(mgr.audit_trail().entries()[0].action, "deploy:production");
    }

    #[test]
    fn rollback_audits_as_security_alert() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();
        mgr.apply(prod_manifest()).unwrap();
        mgr.rollback().unwrap();

        let trail = mgr.audit_trail();
        let rollback_entry = trail.entries().iter().find(|e| e.action == "rollback");
        assert!(rollback_entry.is_some());
        assert_eq!(rollback_entry.unwrap().category, AuditCategory::SecurityAlert);
    }

    #[test]
    fn diff_detects_crate_additions_and_removals() {
        let mut mgr = DeployManager::new();

        let mut m1 = DeployManifest::dev();
        m1.crates.push(CrateSpec { name: "arkhe-core".into(), features: vec![], release: false });

        let mut m2 = DeployManifest::dev();
        m2.crates.push(CrateSpec { name: "arkhe-different".into(), features: vec![], release: false });

        mgr.apply(m1).unwrap();
        let plan = mgr.plan(&m2).unwrap();

        let added = plan.changes.iter().find(|c| c.kind == ChangeKind::CrateAdded);
        let removed = plan.changes.iter().find(|c| c.kind == ChangeKind::CrateRemoved);
        assert!(added.is_some());
        assert!(removed.is_some());
    }

    #[test]
    fn diff_detects_config_changes() {
        let mut mgr = DeployManager::new();

        let mut m1 = DeployManifest::dev();
        m1.config.insert("key".into(), serde_json::json!("old"));

        let mut m2 = DeployManifest::dev();
        m2.config.insert("key".into(), serde_json::json!("new"));

        mgr.apply(m1).unwrap();
        let plan = mgr.plan(&m2).unwrap();

        assert!(plan.changes.iter().any(|c| c.kind == ChangeKind::ConfigChanged));
    }

    #[test]
    fn manifest_from_json() {
        let json = r#"{
            "version": 1,
            "environment": "test",
            "crates": [],
            "config": {},
            "policies": [],
            "metadata": {}
        }"#;
        let manifest = DeployManifest::from_json(json).unwrap();
        assert_eq!(manifest.environment, "test");
    }

    #[test]
    fn manifest_hash_is_deterministic() {
        let m = prod_manifest();
        let h1 = m.hash();
        let h2 = m.hash();
        assert_eq!(h1, h2);
    }

    #[test]
    fn different_manifests_different_hashes() {
        let h1 = dev_manifest().hash();
        let h2 = prod_manifest().hash();
        assert_ne!(h1, h2);
    }

    #[test]
    fn generation_chain() {
        let mut mgr = DeployManager::new();

        let mut m1 = dev_manifest();
        mgr.apply(m1).unwrap();
        let gen1 = mgr.current().unwrap().clone();
        assert!(gen1.previous_generation.is_none());

        mgr.apply(prod_manifest()).unwrap();
        let gen2 = mgr.current().unwrap().clone();
        assert_eq!(gen2.previous_generation.as_ref(), Some(&gen1.id));
    }

    #[test]
    fn rollback_to_nonexistent_fails() {
        let mut mgr = DeployManager::new();
        mgr.apply(dev_manifest()).unwrap();
        let result = mgr.rollback_to(&GenerationId("nonexistent".into()));
        assert!(matches!(result, Err(DeployError::GenerationNotFound { .. })));
    }

    #[test]
    fn with_state_dir_creates_directory() {
        let dir = tempfile::tempdir().unwrap();
        let _mgr = DeployManager::with_state_dir(dir.path()).unwrap();
        assert!(dir.path().exists());
    }
}
