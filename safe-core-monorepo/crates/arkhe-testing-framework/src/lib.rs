// crates/arkhe-testing-framework/src/lib.rs
#![warn(missing_docs)]
#![deny(unsafe_code)]

//! Framework de testes compartilhado para Arkhe OS.
//!
//! Fornece:
//! - Fixtures comuns (DIDs, configs, manifests)
//! - Assert macros customizadas
//! - Helpers para testes assíncronos
//! - Relatório de cobertura de testes por crate

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// DID de teste padrão.
pub const TEST_DID: &str = "did:arkhe:test";
/// DID de admin de teste.
pub const ADMIN_DID: &str = "did:arkhe:admin";
/// DID de usuário de teste.
pub const USER_DID: &str = "did:arkhe:user";

/// Cria um DID de teste com o nome dado.
pub fn test_did(name: &str) -> String {
    format!("did:arkhe:{}", name)
}

/// Configuração de teste padrão.
pub fn test_config() -> serde_json::Value {
    serde_json::json!({
        "admin_mode": false,
        "log.level": "warn",
        "telemetry.otlp_endpoint": null
    })
}

/// Configuração de teste com admin mode.
pub fn admin_config() -> serde_json::Value {
    serde_json::json!({
        "admin_mode": true,
        "log.level": "debug"
    })
}

/// Resultado de um teste de propriedade.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PropertyTestReport {
    pub property_name: String,
    pub cases_run: u32,
    pub passed: u32,
    pub failed: u32,
    pub failures: Vec<String>,
}

impl PropertyTestReport {
    pub fn new(name: &str) -> Self {
        Self {
            property_name: name.into(),
            cases_run: 0,
            passed: 0,
            failed: 0,
            failures: Vec::new(),
        }
    }

    pub fn record_pass(&mut self) {
        self.cases_run += 1;
        self.passed += 1;
    }

    pub fn record_fail(&mut self, reason: &str) {
        self.cases_run += 1;
        self.failed += 1;
        self.failures.push(reason.into());
    }

    pub fn is_success(&self) -> bool {
        self.failed == 0
    }
}

/// Resultado agregado de uma suite de testes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuiteReport {
    pub suite_name: String,
    pub tests: Vec<PropertyTestReport>,
    pub total_passed: u32,
    pub total_failed: u32,
}

impl SuiteReport {
    pub fn new(name: &str) -> Self {
        Self {
            suite_name: name.into(),
            tests: Vec::new(),
            total_passed: 0,
            total_failed: 0,
        }
    }

    pub fn add(&mut self, report: PropertyTestReport) {
        self.total_passed += report.passed;
        self.total_failed += report.failed;
        self.tests.push(report);
    }

    pub fn is_success(&self) -> bool {
        self.total_failed == 0
    }
}

/// Executa uma função de teste N vezes, coletando resultados.
pub fn run_property<F>(name: &str, iterations: u32, mut f: F) -> PropertyTestReport
where
    F: FnMut(u32) -> Result<(), String>,
{
    let mut report = PropertyTestReport::new(name);
    for i in 0..iterations {
        match f(i) {
            Ok(()) => report.record_pass(),
            Err(reason) => report.record_fail(&reason),
        }
    }
    report
}

/// Assert que dois valores JSON são iguais (com mensagem customizada).
pub fn assert_json_eq(a: &serde_json::Value, b: &serde_json::Value, msg: &str) {
    if a != b {
        panic!(
            "{}\n  left:  {}\n  right: {}",
            msg,
            serde_json::to_string_pretty(a).unwrap_or_default(),
            serde_json::to_string_pretty(b).unwrap_or_default(),
        );
    }
}

/// Assert que um resultado é erro contendo substring.
pub fn assert_err_contains<T: std::fmt::Display>(result: &Result<T, impl std::fmt::Display>, substring: &str) {
    match result {
        Err(e) => {
            let msg = e.to_string();
            assert!(msg.contains(substring), "expected error containing '{}', got: '{}'", substring, msg);
        }
        Ok(_) => panic!("expected error, got Ok"),
    }
}

/// Fixture de manifesto de deploy para testes.
pub fn test_deploy_manifest() -> serde_json::Value {
    serde_json::json!({
        "version": 1,
        "environment": "test",
        "crates": [
            { "name": "arkhe-core", "features": [], "release": false }
        ],
        "config": {
            "admin_mode": false
        },
        "policies": [],
        "metadata": {}
    })
}

/// Gera um input de política de teste.
pub fn test_policy_input(action: &str, resource: &str) -> serde_json::Value {
    serde_json::json!({
        "actor": TEST_DID,
        "action": action,
        "resource": resource,
        "admin_mode": false
    })
}

/// Gera um input de política de admin.
pub fn admin_policy_input(action: &str, resource: &str) -> serde_json::Value {
    serde_json::json!({
        "actor": ADMIN_DID,
        "action": action,
        "resource": resource,
        "admin_mode": true
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_did_format() {
        assert_eq!(test_did("agent1"), "did:arkhe:agent1");
    }

    #[test]
    fn test_config_is_valid_json() {
        let config = test_config();
        assert_eq!(config["admin_mode"], serde_json::json!(false));
    }

    #[test]
    fn admin_config_has_admin_mode() {
        let config = admin_config();
        assert_eq!(config["admin_mode"], serde_json::json!(true));
    }

    #[test]
    fn property_test_all_pass() {
        let report = run_property("all_pass", 10, |_i| Ok(()));
        assert!(report.is_success());
        assert_eq!(report.cases_run, 10);
        assert_eq!(report.passed, 10);
    }

    #[test]
    fn property_test_some_fail() {
        let report = run_property("some_fail", 10, |i| {
            if i < 7 { Ok(()) } else { Err(format!("failed at {}", i)) }
        });
        assert!(!report.is_success());
        assert_eq!(report.passed, 7);
        assert_eq!(report.failed, 3);
    }

    #[test]
    fn suite_report_aggregation() {
        let mut suite = SuiteReport::new("test_suite");
        suite.add(PropertyTestReport { property_name: "p1".into(), cases_run: 5, passed: 5, failed: 0, failures: vec![] });
        suite.add(PropertyTestReport { property_name: "p2".into(), cases_run: 5, passed: 3, failed: 2, failures: vec!["a".into(), "b".into()] });
        assert!(!suite.is_success());
        assert_eq!(suite.total_passed, 8);
        assert_eq!(suite.total_failed, 2);
    }

    #[test]
    fn assert_json_eq_same() {
        let a = serde_json::json!({"key": "value"});
        assert_json_eq(&a, &a, "should be equal");
    }

    #[test]
    #[should_panic]
    fn assert_json_eq_different() {
        let a = serde_json::json!(1);
        let b = serde_json::json!(2);
        assert_json_eq(&a, &b, "should panic");
    }

    #[test]
    fn assert_err_contains_ok() {
        let result: Result<(), &str> = Err("something went wrong");
        assert_err_contains(&result, "went wrong");
    }

    #[test]
    #[should_panic]
    fn assert_err_contains_on_ok() {
        let result: Result<(), &str> = Ok(());
        assert_err_contains(&result, "anything");
    }

    #[test]
    fn test_policy_input_format() {
        let input = test_policy_input("read", "file.txt");
        assert_eq!(input["actor"], serde_json::json!(TEST_DID));
        assert_eq!(input["admin_mode"], serde_json::json!(false));
    }

    #[test]
    fn admin_policy_input_format() {
        let input = admin_policy_input("delete", "db");
        assert_eq!(input["actor"], serde_json::json!(ADMIN_DID));
        assert_eq!(input["admin_mode"], serde_json::json!(true));
    }

    #[test]
    fn test_deploy_manifest_valid() {
        let manifest = test_deploy_manifest();
        assert_eq!(manifest["environment"], serde_json::json!("test"));
        assert_eq!(manifest["crates"].as_array().unwrap().len(), 1);
    }
}
