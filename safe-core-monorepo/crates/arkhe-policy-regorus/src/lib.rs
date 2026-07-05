// crates/arkhe-policy-regorus/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Motor de políticas Rego/OPA para o Arkhe OS.
//!
//! Permite definir políticas declarativas em Rego que são avaliadas
//! contra um contexto de entrada (input). Integrado com o
//! `arkhe-policy-gateway` para decisions auditáveis.
//!
//! # Exemplo
//!
//! ```
//! use arkhe_policy_regorus::{PolicyEngine, RegoPolicy};
//!
//! let mut engine = PolicyEngine::new();
//! engine.add_policy(RegoPolicy::from_rego_text(
//!     "allow_all",
//!     r#"package arkhe.policy
//!        default allow = false
//!        allow { input.admin_mode }"#,
//! )?);
//!
//! let result = engine.eval_bool(
//!     "arkhe.policy.allow",
//!     &serde_json::json!({"admin_mode": true}),
//! )?;
//! assert_eq!(result, true);
//! ```

use regorus::{Engine, Value};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RegoError {
    #[error("rego compilation error: {0}")]
    Compilation(String),

    #[error("rego evaluation error: {0}")]
    Evaluation(String),

    #[error("policy not found: {0}")]
    PolicyNotFound(String),

    #[error("path not found in result: {0}")]
    PathNotFound(String),

    #[error("type error: expected {expected}, got {actual}")]
    TypeError { expected: String, actual: String },

    #[error("engine error: {0}")]
    Engine(String),
}

impl From<regorus::Error> for RegoError {
    fn from(e: regorus::Error) -> Self {
        RegoError::Engine(e.to_string())
    }
}

pub type RegoResult<T> = Result<T, RegoError>;

/// Uma política Rego compilada.
#[derive(Debug, Clone)]
pub struct RegoPolicy {
    /// Nome da política (identificador único).
    pub name: String,
    /// Código-fonte Rego.
    pub source: String,
}

impl RegoPolicy {
    /// Cria uma política a partir de texto Rego.
    pub fn from_rego_text(name: &str, source: &str) -> RegoResult<Self> {
        // Valida compilando
        let mut engine = Engine::new();
        engine
            .add_policy(name.to_string(), source.to_string())
            .map_err(|e| RegoError::Compilation(format!("{}: {}", name, e)))?;

        Ok(Self {
            name: name.into(),
            source: source.into(),
        })
    }

    /// Cria a política de admin padrão.
    ///
    /// Permite tudo quando `input.admin_mode == true`.
    /// Caso contrário, delega para outras regras.
    pub fn admin_policy() -> Self {
        Self {
            name: "admin_override".into(),
            source: r#"package arkhe.policy

# Default: deny unless explicitly allowed
default allow = false

# Admin mode: permite tudo
allow {
    input.admin_mode == true
}

# Marca que é admin mode para auditoria
is_admin_mode {
    input.admin_mode == true
}
"#
            .into(),
        }
    }

    /// Cria política que permite tudo incondicionalmente (apenas para testes).
    pub fn allow_all() -> Self {
        Self {
            name: "allow_all".into(),
            source: r#"package arkhe.policy
allow = true
"#
            .into(),
        }
    }

    /// Cria política que nega tudo incondicionalmente.
    pub fn deny_all() -> Self {
        Self {
            name: "deny_all".into(),
            source: r#"package arkhe.policy
allow = false
"#
            .into(),
        }
    }
}

/// Resultado de uma avaliação de política.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyEvalResult {
    /// Caminho avaliado (ex: "arkhe.policy.allow").
    pub path: String,
    /// Valor bruto retornado.
    pub value: serde_json::Value,
    /// Se a avaliação sucedeu.
    pub success: bool,
    /// Erro, se houve.
    pub error: Option<String>,
}

impl PolicyEvalResult {
    /// Extrai como booleano.
    pub fn as_bool(&self) -> RegoResult<bool> {
        match &self.value {
            serde_json::Value::Bool(b) => Ok(*b),
            other => Err(RegoError::TypeError {
                expected: "bool".into(),
                actual: format!("{}", other),
            }),
        }
    }

    /// Extrai como string.
    pub fn as_string(&self) -> RegoResult<String> {
        match &self.value {
            serde_json::Value::String(s) => Ok(s.clone()),
            other => Err(RegoError::TypeError {
                expected: "string".into(),
                actual: format!("{}", other),
            }),
        }
    }
}

/// Motor de políticas Rego.
pub struct PolicyEngine {
    policies: Vec<RegoPolicy>,
}

impl PolicyEngine {
    /// Cria motor vazio.
    pub fn new() -> Self {
        Self {
            policies: Vec::new(),
        }
    }

    /// Adiciona uma política ao motor.
    pub fn add_policy(&mut self, policy: RegoPolicy) -> RegoResult<()> {
        // Valida que a política compila
        let mut test_engine = Engine::new();
        test_engine
            .add_policy(policy.name.clone(), policy.source.clone())
            .map_err(|e| RegoError::Compilation(format!("{}: {}", policy.name, e)))?;
        self.policies.push(policy);
        Ok(())
    }

    /// Remove uma política por nome.
    pub fn remove_policy(&mut self, name: &str) -> bool {
        let before = self.policies.len();
        self.policies.retain(|p| p.name != name);
        self.policies.len() < before
    }

    /// Lista nomes das políticas registradas.
    pub fn policy_names(&self) -> Vec<&str> {
        self.policies.iter().map(|p| p.name.as_str()).collect()
    }

    /// Avalia um caminho Rego contra um input, retornando o valor bruto.
    pub fn eval(&self, path: &str, input: &serde_json::Value) -> RegoResult<PolicyEvalResult> {
        let mut engine = Engine::new();

        for policy in &self.policies {
            engine
                .add_policy(policy.name.clone(), policy.source.clone())
                .map_err(|e| RegoError::Compilation(format!("{}: {}", policy.name, e)))?;
        }

        let input_value: Value = serde_json::from_value(input.clone())
            .map_err(|e| RegoError::Evaluation(format!("invalid input JSON: {}", e)))?;

        engine
            .set_input(input_value);

        // Avaliar a expressão
        let result = engine
            .eval_query(path.to_string(), false)
            .map_err(|e| RegoError::Evaluation(e.to_string()))?;

        // Extrair primeiro resultado
        let value = result
            .first()
            .and_then(|r| r.value.as_ref())
            .map(|v| serde_json::to_value(v).unwrap_or(serde_json::Value::Null))
            .unwrap_or(serde_json::Value::Null);

        Ok(PolicyEvalResult {
            path: path.into(),
            value,
            success: true,
            error: None,
        })
    }

    /// Avalia um caminho e retorna como booleano.
    pub fn eval_bool(&self, path: &str, input: &serde_json::Value) -> RegoResult<bool> {
        let result = self.eval(path, input)?;
        result.as_bool()
    }

    /// Avalia um caminho e retorna como string.
    pub fn eval_string(&self, path: &str, input: &serde_json::Value) -> RegoResult<String> {
        let result = self.eval(path, input)?;
        result.as_string()
    }

    /// Avalia allow/deny para o input dado.
    ///
    /// Equivalente a `eval_bool("arkhe.policy.allow", input)`.
    pub fn is_allowed(&self, input: &serde_json::Value) -> RegoResult<bool> {
        self.eval_bool("data.arkhe.policy.allow", input)
    }

    /// Verifica se o input está em admin mode.
    pub fn is_admin_mode(&self, input: &serde_json::Value) -> RegoResult<bool> {
        // Tenta avaliar is_admin_mode; se não existir, assume false
        match self.eval_bool("data.arkhe.policy.is_admin_mode", input) {
            Ok(b) => Ok(b),
            Err(RegoError::PathNotFound(_) | RegoError::TypeError { .. }) => Ok(false),
            Err(e) => Err(e),
        }
    }

    /// Número de políticas registradas.
    pub fn policy_count(&self) -> usize {
        self.policies.len()
    }
}

impl Default for PolicyEngine {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn admin_policy_allows_when_admin_mode_true() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::admin_policy()).unwrap();

        let input = serde_json::json!({
            "admin_mode": true,
            "actor": "did:arkhe:admin"
        });

        assert!(engine.is_allowed(&input).unwrap());
        assert!(engine.is_admin_mode(&input).unwrap());
    }

    #[test]
    fn admin_policy_denies_when_admin_mode_false() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::admin_policy()).unwrap();

        let input = serde_json::json!({
            "admin_mode": false,
            "actor": "did:arkhe:user"
        });

        assert!(!engine.is_allowed(&input).unwrap());
        assert!(!engine.is_admin_mode(&input).unwrap());
    }

    #[test]
    fn allow_all_policy() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::allow_all()).unwrap();

        let input = serde_json::json!({"anything": "goes"});
        assert!(engine.is_allowed(&input).unwrap());
    }

    #[test]
    fn deny_all_policy() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::deny_all()).unwrap();

        let input = serde_json::json!({"admin_mode": true});
        assert!(!engine.is_allowed(&input).unwrap());
    }

    #[test]
    fn custom_policy_with_conditions() {
        let policy = RegoPolicy::from_rego_text(
            "role_based",
            r#"package arkhe.policy

default allow = false

allow {
    input.actor == "did:arkhe:admin"
}

allow {
    input.role == "operator"
    input.action != "delete"
}
"#,
        )
        .unwrap();

        let mut engine = PolicyEngine::new();
        engine.add_policy(policy).unwrap();

        // Admin pode tudo
        assert!(engine.is_allowed(&serde_json::json!({"actor": "did:arkhe:admin", "action": "delete"})).unwrap());

        // Operator pode tudo exceto delete
        assert!(engine.is_allowed(&serde_json::json!({"role": "operator", "action": "read"})).unwrap());
        assert!(!engine.is_allowed(&serde_json::json!({"role": "operator", "action": "delete"})).unwrap());

        // Outros não podem nada
        assert!(!engine.is_allowed(&serde_json::json!({"role": "viewer", "action": "read"})).unwrap());
    }

    #[test]
    fn multiple_policies_last_wins() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::deny_all()).unwrap();
        engine.add_policy(RegoPolicy::allow_all()).unwrap();

        // Regorus: last policy with same path wins
        assert!(engine.is_allowed(&serde_json::json!({})).unwrap());
    }

    #[test]
    fn remove_policy() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::allow_all()).unwrap();
        assert_eq!(engine.policy_count(), 1);

        assert!(engine.remove_policy("allow_all"));
        assert_eq!(engine.policy_count(), 0);
        assert!(!engine.remove_policy("nonexistent"));
    }

    #[test]
    fn policy_names_list() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::admin_policy()).unwrap();
        engine.add_policy(RegoPolicy::allow_all()).unwrap();

        let names = engine.policy_names();
        assert!(names.contains(&"admin_override"));
        assert!(names.contains(&"allow_all"));
    }

    #[test]
    fn invalid_rego_fails_compilation() {
        let result = RegoPolicy::from_rego_text("bad", "this is not valid rego {{{");
        assert!(result.is_err());
    }

    #[test]
    fn eval_generic_path() {
        let mut engine = PolicyEngine::new();
        engine.add_policy(RegoPolicy::from_rego_text(
            "custom",
            r#"package arkhe.score
default trust = 0
trust { input.reputation > 50 }"#,
        ).unwrap());

        let result = engine.eval(
            "data.arkhe.score.trust",
            &serde_json::json!({"reputation": 75}),
        ).unwrap();

        assert!(result.as_bool().unwrap());
    }
}
