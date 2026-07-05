// crates/arkhe-configuration/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Configuração hierárquica para o Arkhe OS.
//!
//! Ordem de precedência (mais alto primeiro):
//! 1. Variáveis de ambiente (ARKHE_*)
//! 2. Configuração programática (set via código)
//! 3. Arquivo de configuração (JSON/TOML)
//! 4. Valores padrão

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("key not found: {0}")]
    NotFound(String),

    #[error("type mismatch for key '{key}': expected {expected}, got {actual}")]
    TypeMismatch { key: String, expected: String, actual: String },

    #[error("parse error for key '{key}': {reason}")]
    ParseError { key: String, reason: String },

    #[error("env var error for '{var}': {reason}")]
    EnvError { var: String, reason: String },
}

pub type ConfigResult<T> = Result<T, ConfigError>;

/// Valor de configuração.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ConfigValue {
    Null,
    Bool(bool),
    Integer(i64),
    Float(f64),
    String(String),
    Array(Vec<ConfigValue>),
    Object(HashMap<String, ConfigValue>),
}

impl ConfigValue {
    pub fn as_bool(&self) -> ConfigResult<bool> {
        match self {
            ConfigValue::Bool(b) => Ok(*b),
            other => Err(ConfigError::TypeMismatch {
                key: String::new(),
                expected: "bool".into(),
                actual: format!("{:?}", other),
            }),
        }
    }

    pub fn as_str(&self) -> ConfigResult<&str> {
        match self {
            ConfigValue::String(s) => Ok(s),
            other => Err(ConfigError::TypeMismatch {
                key: String::new(),
                expected: "string".into(),
                actual: format!("{:?}", other),
            }),
        }
    }

    pub fn as_i64(&self) -> ConfigResult<i64> {
        match self {
            ConfigValue::Integer(i) => Ok(*i),
            other => Err(ConfigError::TypeMismatch {
                key: String::new(),
                expected: "integer".into(),
                actual: format!("{:?}", other),
            }),
        }
    }

    pub fn as_f64(&self) -> ConfigResult<f64> {
        match self {
            ConfigValue::Float(f) => Ok(*f),
            ConfigValue::Integer(i) => Ok(*i as f64),
            other => Err(ConfigError::TypeMismatch {
                key: String::new(),
                expected: "number".into(),
                actual: format!("{:?}", other),
            }),
        }
    }
}

impl From<serde_json::Value> for ConfigValue {
    fn from(v: serde_json::Value) -> Self {
        match v {
            serde_json::Value::Null => ConfigValue::Null,
            serde_json::Value::Bool(b) => ConfigValue::Bool(b),
            serde_json::Value::Number(n) => {
                if let Some(i) = n.as_i64() {
                    ConfigValue::Integer(i)
                } else if let Some(f) = n.as_f64() {
                    ConfigValue::Float(f)
                } else {
                    ConfigValue::Null
                }
            }
            serde_json::Value::String(s) => ConfigValue::String(s),
            serde_json::Value::Array(arr) => {
                ConfigValue::Array(arr.into_iter().map(ConfigValue::from).collect())
            }
            serde_json::Value::Object(obj) => {
                ConfigValue::Object(obj.into_iter().map(|(k, v)| (k, ConfigValue::from(v))).collect())
            }
        }
    }
}

impl From<ConfigValue> for serde_json::Value {
    fn from(v: ConfigValue) -> Self {
        match v {
            ConfigValue::Null => serde_json::Value::Null,
            ConfigValue::Bool(b) => serde_json::Value::Bool(b),
            ConfigValue::Integer(i) => serde_json::json!(i),
            ConfigValue::Float(f) => serde_json::json!(f),
            ConfigValue::String(s) => serde_json::Value::String(s),
            ConfigValue::Array(arr) => {
                serde_json::Value::Array(arr.into_iter().map(serde_json::Value::from).collect())
            }
            ConfigValue::Object(obj) => {
                serde_json::Value::Object(
                    obj.into_iter()
                        .map(|(k, v)| (k, serde_json::Value::from(v)))
                        .collect(),
                )
            }
        }
    }
}

/// Configuração hierárquica.
pub struct Configuration {
    /// Valores setados programaticamente (mais alta prioridade após env).
    overrides: HashMap<String, ConfigValue>,
    /// Valores do arquivo de config.
    file_values: HashMap<String, ConfigValue>,
    /// Mapeamento de env vars para keys (ARKHE_ADMIN_MODE → admin_mode).
    env_mappings: HashMap<String, String>,
}

impl Configuration {
    pub fn new() -> Self {
        let mut env_mappings = HashMap::new();

        // Mapeamentos padrão ARKHE_* → keys
        env_mappings.insert("ARKHE_ADMIN_MODE".into(), "admin_mode".into());
        env_mappings.insert("ARKHE_LOG_LEVEL".into(), "log.level".into());
        env_mappings.insert("ARKHE_OTLP_ENDPOINT".into(), "telemetry.otlp_endpoint".into());
        env_mappings.insert("ARKHE_WORMGRAPH_PATH".into(), "wormgraph.storage_path".into());
        env_mappings.insert("ARKHE_POLICY_DIR".into(), "policy.directory".into());
        env_mappings.insert("ARKHE_SECRETS_PATH".into(), "secrets.path".into());
        env_mappings.insert("ARKHE_LLM_DEFAULT_MODEL".into(), "llm.default_model".into());

        Self {
            overrides: HashMap::new(),
            file_values: HashMap::new(),
            env_mappings,
        }
    }

    /// Carrega configuração de um JSON string.
    pub fn load_json(&mut self, json: &str) -> ConfigResult<()> {
        let v: serde_json::Value =
            serde_json::from_str(json).map_err(|e| ConfigError::ParseError {
                key: "_root".into(),
                reason: e.to_string(),
            })?;

        self.load_value(&v, "");
        Ok(())
    }

    fn load_value(&mut self, value: &serde_json::Value, prefix: &str) {
        match value {
            serde_json::Value::Object(map) => {
                for (k, v) in map {
                    let key = if prefix.is_empty() {
                        k.clone()
                    } else {
                        format!("{}.{}", prefix, k)
                    };
                    self.load_value(v, &key);
                }
            }
            other => {
                if let Some(key) = self.normalize_key(prefix) {
                    self.file_values.insert(key, ConfigValue::from(other.clone()));
                }
            }
        }
    }

    fn normalize_key(&self, key: &str) -> Option<String> {
        if key.is_empty() {
            return None;
        }
        Some(key.to_lowercase().replace('_', "."))
    }

    /// Seta um valor programaticamente (override).
    pub fn set(&mut self, key: &str, value: ConfigValue) {
        let normalized = key.to_lowercase().replace('_', ".");
        self.overrides.insert(normalized, value);
    }

    /// Seta um valor bool.
    pub fn set_bool(&mut self, key: &str, value: bool) {
        self.set(key, ConfigValue::Bool(value));
    }

    /// Seta um valor string.
    pub fn set_string(&mut self, key: &str, value: &str) {
        self.set(key, ConfigValue::String(value.into()));
    }

    /// Obtém um valor, respeitando a precedência.
    pub fn get(&self, key: &str) -> ConfigResult<ConfigValue> {
        let normalized = key.to_lowercase().replace('_', ".");

        // 1. Overrides
        if let Some(v) = self.overrides.get(&normalized) {
            return Ok(v.clone());
        }

        // 2. Env vars
        for (env_var, config_key) in &self.env_mappings {
            if *config_key == normalized {
                if let Ok(val) = env::var(env_var) {
                    return Ok(parse_env_value(&val));
                }
            }
        }

        // 3. File values
        if let Some(v) = self.file_values.get(&normalized) {
            return Ok(v.clone());
        }

        Err(ConfigError::NotFound(key.into()))
    }

    /// Obtém como bool.
    pub fn get_bool(&self, key: &str) -> ConfigResult<bool> {
        self.get(key)?.as_bool().map_err(|e| ConfigError::TypeMismatch {
            key: key.into(),
            expected: "bool".into(),
            actual: e.actual,
        })
    }

    /// Obtém como string.
    pub fn get_string(&self, key: &str) -> ConfigResult<String> {
        self.get(key)?.as_str().map(|s| s.to_string()).map_err(|e| {
            ConfigError::TypeMismatch {
                key: key.into(),
                expected: "string".into(),
                actual: e.actual,
            }
        })
    }

    /// Obtém como i64.
    pub fn get_i64(&self, key: &str) -> ConfigResult<i64> {
        self.get(key)?.as_i64().map_err(|e| ConfigError::TypeMismatch {
            key: key.into(),
            expected: "integer".into(),
            actual: e.actual,
        })
    }

    /// Obtém como string, com fallback.
    pub fn get_string_or(&self, key: &str, default: &str) -> String {
        self.get_string(key).unwrap_or_else(|_| default.into())
    }

    /// Obtém como bool, com fallback.
    pub fn get_bool_or(&self, key: &str, default: bool) -> bool {
        self.get_bool(key).unwrap_or(default)
    }

    /// Verifica se admin mode está ativo.
    ///
    /// Lê `ARKHE_ADMIN_MODE` env var, override, ou arquivo config.
    pub fn is_admin_mode(&self) -> bool {
        self.get_bool_or("admin_mode", false)
    }

    /// Registra mapeamento de env var adicional.
    pub fn register_env_mapping(&mut self, env_var: &str, config_key: &str) {
        self.env_mappings.insert(env_var.into(), config_key.to_lowercase().replace('_', "."));
    }

    /// Lista todas as chaves disponíveis (sem duplicatas).
    pub fn keys(&self) -> Vec<String> {
        let mut set = std::collections::HashSet::new();
        for k in self.overrides.keys() {
            set.insert(k.clone());
        }
        for k in self.file_values.keys() {
            set.insert(k.clone());
        }
        for k in self.env_mappings.values() {
            set.insert(k.clone());
        }
        let mut keys: Vec<_> = set.into_iter().collect();
        keys.sort();
        keys
    }
}

impl Default for Configuration {
    fn default() -> Self {
        Self::new()
    }
}

/// Parseia um valor de env var para ConfigValue.
fn parse_env_value(s: &str) -> ConfigValue {
    let lower = s.to_lowercase();
    if lower == "true" || lower == "1" || lower == "yes" {
        return ConfigValue::Bool(true);
    }
    if lower == "false" || lower == "0" || lower == "no" {
        return ConfigValue::Bool(false);
    }
    if let Ok(i) = s.parse::<i64>() {
        return ConfigValue::Integer(i);
    }
    if let Ok(f) = s.parse::<f64>() {
        return ConfigValue::Float(f);
    }
    ConfigValue::String(s.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_admin_mode_is_false() {
        // Limpa env var se existir
        env::remove_var("ARKHE_ADMIN_MODE");
        let config = Configuration::new();
        assert!(!config.is_admin_mode());
    }

    #[test]
    fn override_admin_mode() {
        let mut config = Configuration::new();
        config.set_bool("admin_mode", true);
        assert!(config.is_admin_mode());
    }

    #[test]
    fn env_var_admin_mode() {
        env::set_var("ARKHE_ADMIN_MODE", "true");
        let config = Configuration::new();
        assert!(config.is_admin_mode());
        env::remove_var("ARKHE_ADMIN_MODE");
    }

    #[test]
    fn env_var_false_values() {
        for val in ["false", "0", "no", "FALSE"] {
            env::set_var("ARKHE_ADMIN_MODE", val);
            let config = Configuration::new();
            assert!(!config.is_admin_mode(), "failed for value: {}", val);
        }
        env::remove_var("ARKHE_ADMIN_MODE");
    }

    #[test]
    fn override_takes_precedence_over_env() {
        env::set_var("ARKHE_ADMIN_MODE", "true");
        let mut config = Configuration::new();
        config.set_bool("admin_mode", false);
        assert!(!config.is_admin_mode());
        env::remove_var("ARKHE_ADMIN_MODE");
    }

    #[test]
    fn env_takes_precedence_over_file() {
        env::set_var("ARKHE_ADMIN_MODE", "true");
        let mut config = Configuration::new();
        config.load_json(r#"{"admin_mode": false}"#).unwrap();
        assert!(config.is_admin_mode());
        env::remove_var("ARKHE_ADMIN_MODE");
    }

    #[test]
    fn file_config_loading() {
        let mut config = Configuration::new();
        config
            .load_json(r#"{
                "admin_mode": true,
                "log": { "level": "debug" },
                "llm": { "default_model": "luna-70b" }
            }"#)
            .unwrap();

        assert!(config.get_bool("admin_mode").unwrap());
        assert_eq!(config.get_string("log.level").unwrap(), "debug");
        assert_eq!(config.get_string("llm.default_model").unwrap(), "luna-70b");
    }

    #[test]
    fn key_normalization() {
        let mut config = Configuration::new();
        config.set_bool("admin_mode", true);

        // Todas as formas devem funcionar
        assert!(config.get_bool("admin_mode").is_ok());
        assert!(config.get_bool("admin.mode").is_ok());
        assert!(config.get_bool("ADMIN_MODE").is_ok());
    }

    #[test]
    fn get_string_or_fallback() {
        let config = Configuration::new();
        assert_eq!(config.get_string_or("nonexistent", "default"), "default");
        assert_eq!(config.get_bool_or("nonexistent", true), true);
    }

    #[test]
    fn env_var_parsing_types() {
        env::set_var("ARKHE_TEST_INT", "42");
        env::set_var("ARKHE_TEST_FLOAT", "3.14");
        env::set_var("ARKHE_TEST_STR", "hello");

        let mut config = Configuration::new();
        config.register_env_mapping("ARKHE_TEST_INT", "test.int");
        config.register_env_mapping("ARKHE_TEST_FLOAT", "test.float");
        config.register_env_mapping("ARKHE_TEST_STR", "test.str");

        assert_eq!(config.get_i64("test.int").unwrap(), 42);
        assert!((config.get("test.float").unwrap().as_f64().unwrap() - 3.14).abs() < 1e-10);
        assert_eq!(config.get_string("test.str").unwrap(), "hello");

        env::remove_var("ARKHE_TEST_INT");
        env::remove_var("ARKHE_TEST_FLOAT");
        env::remove_var("ARKHE_TEST_STR");
    }

    #[test]
    fn keys_list() {
        let mut config = Configuration::new();
        config.set_bool("a.b", true);
        config.set_string("c.d", "val");
        let keys = config.keys();
        assert!(keys.contains(&"a.b".to_string()));
        assert!(keys.contains(&"c.d".to_string()));
        // admin_mode from env mapping
        assert!(keys.contains(&"admin_mode".to_string()));
    }

    #[test]
    fn not_found_error() {
        let config = Configuration::new();
        let result = config.get("absolutely.nonexistent.key");
        assert!(matches!(result, Err(ConfigError::NotFound(_))));
    }
}
