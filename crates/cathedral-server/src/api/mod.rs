pub mod auth;
pub mod compile;

use axum::{routing::{get, post}, Router, middleware};
use std::sync::Arc;
use crate::orchestration::Orchestrator;

pub fn create_routes(orchestrator: Arc<Orchestrator>) -> Router {
    let api_routes = Router::new()
        .route("/compile", post(compile::compile_contract))
        .layer(middleware::from_fn(auth::did_auth_middleware))
        .with_state(orchestrator.clone());

    Router::new()
        .route("/health", get(health_check))
        .nest("/api", api_routes)
        .with_state(orchestrator)
}

async fn health_check() -> &'static str {
    "OK"
}
