use crate::state::BridgeState;
use axum::{Router, routing::get};
use std::sync::Arc;

pub fn router(_state: Arc<BridgeState>) -> Router {
    Router::new().route("/health", get(|| async { "ok" }))
}
