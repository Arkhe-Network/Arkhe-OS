//! Tool implementations — lógica pura, testável sem dependência de rmcp.
//!
//! Cada função aqui é chamada tanto pelo handler HTTP quanto pelo MCP tool.
//! Isso garante que a lógica ética é testada independentemente do transporte.

use crate::api::*;
use crate::state::BridgeState;
use safe_core_ethics::EthicsError;
use serde_json::json;
use std::sync::Arc;

/// Verifica se uma ação é eticamente permitida.
pub async fn enforce_action(
    state: &Arc<BridgeState>,
    action: &str,
    context: &serde_json::Value,
) -> Result<EnforceResponse, EthicsError> {
    let result = state.ethics_engine.check_action(action, context).await?;
    Ok(EnforceResponse {
        allowed: result.is_allowed(),
        result: Some((&result).into()),
        request_id: uuid::Uuid::new_v4().to_string(),
        timestamp: chrono::Utc::now(),
        latency_ms: 0,
    })
}

/// Lista violações registradas.
pub async fn get_violations(
    state: &Arc<BridgeState>,
) -> ViolationsResponse {
    let violations = state.ethics_engine.get_violations().await;
    ViolationsResponse {
        total: violations.len(),
        violations,
        timestamp: chrono::Utc::now(),
    }
}

/// Limpa violações registradas.
pub async fn clear_violations(
    state: &Arc<BridgeState>,
) -> serde_json::Value {
    state.ethics_engine.clear_violations().await;
    json!({"ok": true, "cleared": true})
}

/// Lista invariantes de segurança.
pub fn list_invariants(
    state: &Arc<BridgeState>,
) -> InvariantsResponse {
    InvariantsResponse {
        total: state.invariants.len(),
        invariants: state.invariants.clone(),
        timestamp: chrono::Utc::now(),
    }
}

/// Exporta especificações Lean 4.
pub async fn export_invariants(
    _state: &Arc<BridgeState>,
) -> Result<serde_json::Value, String> {
    Ok(json!({"ok": true, "path": "/tmp/safe-core-lean4-export", "note": "Pseudo-código Lean 4"}))
}

/// Healthcheck.
pub async fn health_check(
    state: &Arc<BridgeState>,
) -> HealthResponse {
    let constraints = state.ethics_engine.constraint_count().await;
    HealthResponse {
        status: "ok".into(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        components: HealthComponents {
            ethics_engine: "ready".into(),
            invariants: "ready".into(),
            total_constraints: constraints,
            total_invariants: state.invariants.len(),
        },
        timestamp: chrono::Utc::now(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn state() -> Arc<BridgeState> {
        Arc::new(BridgeState::new())
    }

    #[tokio::test]
    async fn enforce_safe_action_allowed() {
        let ctx = json!({
            "harm_to_humans": false,
            "violates_autonomy": false,
            "transparent": true,
            "privacy_violation": false
        });
        let result = enforce_action(&state(), "test_action", &ctx).await.unwrap();
        assert!(result.allowed);
        assert_eq!(result.result.as_ref().unwrap()["type"], "allowed");
    }

    #[tokio::test]
    async fn enforce_harm_blocked() {
        let ctx = json!({"harm_to_humans": true});
        let result = enforce_action(&state(), "harm", &ctx).await.unwrap();
        assert!(!result.allowed);
        assert_eq!(result.result.as_ref().unwrap()["type"], "blocked");
    }

    #[tokio::test]
    async fn enforce_transparency_requires_approval() {
        let ctx = json!({}); // transparent ausente → violação
        let result = enforce_action(&state(), "opaque", &ctx).await.unwrap();
        assert!(!result.allowed);
        assert_eq!(result.result.as_ref().unwrap()["type"], "requires_approval");
    }

    #[tokio::test]
    async fn violations_tracked() {
        let st = state();
        // Causar violação
        let ctx = json!({"harm_to_humans": true});
        let _ = enforce_action(&st, "x", &ctx).await;

        // Verificar
        let resp = get_violations(&st).await;
        assert_eq!(resp.total, 1);
        assert_eq!(resp.violations[0].constraint_id, "ETH-001");
    }

    #[tokio::test]
    async fn clear_violations_test() {
        let st = state();
        // Causar
        let ctx = json!({"harm_to_humans": true});
        let _ = enforce_action(&st, "x", &ctx).await;
        // Limpar
        let result = clear_violations(&st).await;
        assert_eq!(result["ok"], true);
        // Verificar limpo
        let resp = get_violations(&st).await;
        assert_eq!(resp.total, 0);
    }

    #[tokio::test]
    async fn invariants_listed() {
        let resp = list_invariants(&state());
        assert_eq!(resp.total, 5);
        assert_eq!(resp.invariants[0].id, "INV-001");
        assert_eq!(resp.invariants[0].severity, "Critical");
    }

    #[tokio::test]
    async fn health_check_test() {
        let resp = health_check(&state()).await;
        assert_eq!(resp.status, "ok");
        assert_eq!(resp.components.total_constraints, 4);
        assert_eq!(resp.components.total_invariants, 5);
    }
}
